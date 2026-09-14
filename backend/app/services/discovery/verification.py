"""Active opportunity re-verification (spec §22-23, §55-56, §67).

Discovery is not enough: published listings are revisited.

- Deadline passed (a fact from the stored deadline) → source_state DEADLINE_PASSED, status EXPIRED
  (`content_lifecycle_service.expire_content`, also run hourly by the scheduler).
- Listings from complete-listing sources (public ATS boards) are verified by every source run: a
  listing missing from a complete fetch is marked SOURCE_REMOVED pending admin confirmation
  (pipeline.py). They are not fetched again here.
- Other published listings with an official URL are re-fetched politely:
    404/410 → SOURCE_REMOVED (pending confirmation)
    redirect to a different site → UNKNOWN_REQUIRES_REVIEW (pending confirmation)
    page states the listing is closed → CLOSED (pending confirmation)
    200 → last_verified_at refreshed
    access denied / robots / network errors → nothing changes (never treated as removal)

Nothing is deleted: saved items, applications and CV analyses keep their references, and detail
pages show the listing's state instead of an Apply button.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.ingestion.http_client import AccessDeniedError, DiscoveryHttpClient, FetchError, NotFoundError, RobotsDisallowedError
from app.ingestion.text import html_to_text
from app.ingestion.url_safety import registrable_domain
from app.models.admin_ops import ContentSource, DiscoveryRun, DiscoveryRunStatus, DiscoveryRunTrigger, DiscoveryRunType
from app.models.job import ContentStatus, Job, SourceState
from app.models.scholarship import Scholarship
from app.services import audit_service, content_lifecycle_service
from app.services.discovery import publishing
from app.services.discovery.records import ENTITY_JOB, ENTITY_SCHOLARSHIP

logger = logging.getLogger("careeros.discovery.verification")

COMPLETE_LISTING_SOURCE_TYPES = {"GREENHOUSE", "LEVER", "ASHBY", "SMARTRECRUITERS", "WORKDAY"}
_CLOSED_PHRASES = re.compile(
    r"(no longer accepting applications|this (job|position|role|vacancy|posting) (is|has been) (closed|filled|expired)"
    r"|applications (are|have) (now )?closed|the application (deadline|period) has (passed|ended)|position has been filled"
    r"|this job is no longer available|job not found|vacancy (is )?closed)",
    re.IGNORECASE,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def verify_active_opportunities(
    db: AsyncSession, *, settings: Settings | None = None, http_client: DiscoveryHttpClient | None = None, trigger: DiscoveryRunTrigger = DiscoveryRunTrigger.SCHEDULED
) -> DiscoveryRun:
    settings = settings or get_settings()
    now = _now()
    run = DiscoveryRun(run_type=DiscoveryRunType.VERIFICATION, trigger=trigger, status=DiscoveryRunStatus.RUNNING, queued_at=now, started_at=now, stats_json={})
    db.add(run)
    await db.commit()

    expired = await content_lifecycle_service.expire_content(db)
    stats = {"deadline_passed": expired, "checked": 0, "removed": 0, "closed": 0, "redirected": 0, "verified": 0, "skipped": 0}
    if not settings.web_discovery_enabled:
        run.status = DiscoveryRunStatus.SKIPPED
        run.error_code = "DISABLED"
    else:
        client = http_client or DiscoveryHttpClient(
            user_agent=settings.discovery_user_agent, timeout_seconds=settings.discovery_request_timeout_seconds,
            max_response_bytes=settings.discovery_max_response_bytes, max_requests=settings.verification_max_items_per_run + 20,
            min_interval_seconds=settings.discovery_min_request_interval_seconds,
        )
        try:
            await _recheck_urls(db, client, settings, stats, now)
        finally:
            if http_client is None:
                await client.aclose()
        run.status = DiscoveryRunStatus.SUCCEEDED
    run.finished_at = _now()
    run.duration_ms = int((run.finished_at - now).total_seconds() * 1000)
    run.items_found = stats["checked"]
    run.items_removed = stats["removed"] + stats["closed"] + stats["redirected"]
    run.stats_json = stats
    audit_service.add(db, admin_id=None, action="verification_run", entity_type="discovery_run", entity_id=run.id, metadata=stats)
    await db.commit()
    return run


async def _recheck_urls(db: AsyncSession, client: DiscoveryHttpClient, settings: Settings, stats: dict, now: datetime) -> None:
    stale_before = now - timedelta(hours=settings.verification_interval_hours)
    candidates: list[tuple[str, object]] = []
    for model, entity_type, url_attr in ((Job, ENTITY_JOB, "application_url"), (Scholarship, ENTITY_SCHOLARSHIP, "official_url")):
        rows = (await db.execute(
            select(model)
            .where(model.status == ContentStatus.PUBLISHED, model.source_state == SourceState.ACTIVE, model.is_demo.is_(False),
                   or_(getattr(model, url_attr).isnot(None), model.source_url.isnot(None)))
            .order_by(model.last_verified_at.asc().nulls_first())
            .limit(settings.verification_max_items_per_run)
        )).scalars().all()
        candidates += [(entity_type, row) for row in rows]

    source_types = {
        s.id: s.source_type.value for s in (await db.execute(select(ContentSource))).scalars().all()
    }
    for entity_type, entity in candidates[: settings.verification_max_items_per_run]:
        verified_at = _aware(entity.last_verified_at)
        if verified_at and verified_at > stale_before:
            continue
        if source_types.get(entity.content_source_id) in COMPLETE_LISTING_SOURCE_TYPES:
            continue  # verified by its source runs instead
        url = (entity.application_url if entity_type == ENTITY_JOB else entity.official_url) or entity.source_url
        stats["checked"] += 1
        try:
            response = await client.fetch(url)
        except NotFoundError:
            await _pending_state(db, entity_type, entity, SourceState.SOURCE_REMOVED, reason="not_found")
            stats["removed"] += 1
            continue
        except (AccessDeniedError, RobotsDisallowedError):
            stats["skipped"] += 1  # access-controlled: never bypassed, never read as "removed"
            continue
        except FetchError:
            stats["skipped"] += 1
            continue
        if response.redirected and registrable_domain(response.url) != registrable_domain(url):
            await _pending_state(db, entity_type, entity, SourceState.UNKNOWN_REQUIRES_REVIEW, reason="redirected_elsewhere")
            stats["redirected"] += 1
            continue
        text = html_to_text(response.text, max_length=50_000) or ""
        if _CLOSED_PHRASES.search(text):
            await _pending_state(db, entity_type, entity, SourceState.CLOSED, reason="page_states_closed")
            stats["closed"] += 1
            continue
        entity.last_verified_at = _now()
        stats["verified"] += 1
        await db.commit()


async def _pending_state(db: AsyncSession, entity_type: str, entity, new_state: SourceState, *, reason: str) -> None:
    await publishing.record_change(
        db, entity_type=entity_type, entity_id=entity.id, field="source_state", old=entity.source_state.value, new=new_state.value,
        source_id=entity.content_source_id, item_id=None,
    )
    entity.source_state = new_state
    audit_service.add(db, admin_id=None, action="source_removed" if new_state == SourceState.SOURCE_REMOVED else "source_state_changed",
                      entity_type=entity_type.lower(), entity_id=entity.id, metadata={"state": new_state.value, "reason": reason})
    await db.commit()
