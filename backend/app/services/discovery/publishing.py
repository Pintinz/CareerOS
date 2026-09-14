"""Creating drafts / publishing from discovered items, applying detected changes, and follower
notifications. Shared by the admin review flow and the (default-off) auto-publish path."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.ingestion.schemas import ExtractedIntelligence, ExtractedJob, ExtractedScholarship, parse_record, record_canonical_url
from app.ingestion.url_safety import is_aggregator_url
from app.models.admin_ops import (
    ChangeStatus,
    ContentChange,
    ContentSource,
    DiscoveredItem,
    DiscoveredItemStatus,
    ItemVerificationStatus,
    VerificationStatus,
)
from app.models.company import Company
from app.models.company_follow import CompanyFollow
from app.models.intelligence_post import IntelligencePost
from app.models.job import ContentStatus, Job, SourceState
from app.models.push import DeviceToken, NotificationPreferences
from app.models.scholarship import Scholarship
from app.repositories.company_repository import CompanyRepository
from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.job_repository import JobRepository
from app.repositories.scholarship_repository import ScholarshipRepository
from app.services import audit_service
from app.services.discovery.records import (
    ENTITY_INTELLIGENCE,
    ENTITY_JOB,
    ENTITY_SCHOLARSHIP,
    build_intelligence,
    build_job,
    build_scholarship,
    coerce_for_field,
    entity_type_for,
)
from app.services.push_provider import MockPushProvider, PushProvider

logger = logging.getLogger("careeros.discovery.publishing")

MODEL_FOR_ENTITY = {ENTITY_JOB: Job, ENTITY_SCHOLARSHIP: Scholarship, ENTITY_INTELLIGENCE: IntelligencePost}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


async def load_entity(db: AsyncSession, entity_type: str | None, entity_id: str | None):
    if not entity_type or not entity_id:
        return None
    return await db.get(MODEL_FOR_ENTITY[entity_type], entity_id)


async def linked_entity(db: AsyncSession, item: DiscoveredItem):
    entity_type = item.matched_entity_type or entity_type_for(item.item_type)
    entity_id = item.matched_entity_id or item.created_draft_id
    return entity_type, await load_entity(db, entity_type, entity_id)


def record_with_overrides(item: DiscoveredItem, overrides: dict | None):
    data = dict(item.extracted_data_json or {})
    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})
    try:
        return parse_record(data)
    except (ValidationError, ValueError) as exc:
        raise _unprocessable("The edited fields are not valid.") from exc


def auto_publish_gates(settings: Settings, *, source: ContentSource, item: DiscoveredItem, company: Company | None) -> list[str]:
    """Reasons auto-publishing is NOT allowed (empty list = allowed). Every gate must pass."""
    reasons = []
    if not settings.auto_publish_discovery:
        reasons.append("AUTO_PUBLISH_DISCOVERY is off")
    if not source.auto_publish_allowed:
        reasons.append("source does not allow auto-publish")
    if source.trust_level < 4:
        reasons.append("source trust level below 4")
    if source.verification_status != VerificationStatus.VERIFIED:
        reasons.append("source ownership not verified by an admin")
    if item.verification_status != ItemVerificationStatus.SOURCE_VERIFIED:
        reasons.append("item not source-verified")
    if item.status == DiscoveredItemStatus.DUPLICATE or item.matched_entity_id:
        reasons.append("duplicate or update of an existing record")
    evidence = item.evidence_json or {}
    if evidence.get("injection_suspected") or evidence.get("flags"):
        reasons.append("evidence flags present")
    if entity_type_for(item.item_type) in (ENTITY_JOB,) and company is None:
        reasons.append("no matched company")
    if source.source_type.value == "AGGREGATOR":
        reasons.append("discovery-only source")
    return reasons


async def materialize_item(
    db: AsyncSession,
    item: DiscoveredItem,
    *,
    publish: bool,
    admin_id: str | None,
    overrides: dict | None = None,
    company_id: str | None = None,
) -> tuple[str, object]:
    """Create (or, if a draft already exists, update/publish) the CareerOS record for an item.
    Does not commit."""
    source = await db.get(ContentSource, item.source_id)
    if source is None:
        raise _unprocessable("The item's source no longer exists.")
    record = record_with_overrides(item, overrides)
    entity_type = entity_type_for(record.content_type)

    if publish and is_aggregator_url(record_canonical_url(record)):
        # Tier-4 sites may help find a listing but never become its canonical source.
        raise _unprocessable("This listing points to a discovery-only site. Add the official application or source URL before publishing.")

    verified = item.verification_status == ItemVerificationStatus.SOURCE_VERIFIED and source.verification_status == VerificationStatus.VERIFIED
    target_status = ContentStatus.PUBLISHED if publish else ContentStatus.DRAFT
    now = _now()

    existing = await load_entity(db, entity_type, item.created_draft_id) if item.created_draft_id else None
    if existing is not None:
        if publish and existing.status != ContentStatus.PUBLISHED:
            existing.status = ContentStatus.PUBLISHED
            existing.published_at = existing.published_at or now
            existing.published_by_admin_id = existing.published_by_admin_id or admin_id
        entity = existing
    elif entity_type == ENTITY_JOB:
        assert isinstance(record, ExtractedJob)
        resolved_company_id = company_id or item.company_id
        company = await db.get(Company, resolved_company_id) if resolved_company_id else None
        if company is None:
            raise _unprocessable("Choose or create the company for this job before creating a draft.")
        slug = await JobRepository(db).generate_unique_slug(record.title, company.name)
        entity = build_job(record, source=source, company_id=company.id, slug=slug, status=target_status, admin_id=admin_id, verified=verified)
        db.add(entity)
    elif entity_type == ENTITY_SCHOLARSHIP:
        assert isinstance(record, ExtractedScholarship)
        slug = await ScholarshipRepository(db).generate_unique_slug(record.name)
        entity = build_scholarship(record, source=source, slug=slug, status=target_status, admin_id=admin_id, verified=verified)
        db.add(entity)
    else:
        assert isinstance(record, ExtractedIntelligence)
        slug = await IntelligenceRepository(db).generate_unique_slug(record.headline)
        entity = build_intelligence(
            record, source=source, company_id=company_id or item.company_id, slug=slug, status=target_status, admin_id=admin_id, verified=verified
        )
        db.add(entity)

    if publish:
        entity.published_at = entity.published_at or now
        entity.published_by_admin_id = entity.published_by_admin_id or admin_id
        entity.reviewed_by_admin_id = entity.reviewed_by_admin_id or admin_id
    await db.flush()

    item.created_draft_id = entity.id
    item.status = DiscoveredItemStatus.PUBLISHED if publish else DiscoveredItemStatus.DRAFT_CREATED
    item.reviewed_by_admin_id = admin_id
    item.reviewed_at = now
    audit_service.add(
        db, admin_id=admin_id, action="discovery_published" if publish else "discovery_draft_created",
        entity_type="discovered_item", entity_id=item.id, metadata={"entity_type": entity_type, "entity_id": entity.id},
    )
    return entity_type, entity


async def create_company_from_proposal(db: AsyncSession, item: DiscoveredItem, *, admin_id: str | None, fields: dict) -> Company:
    """Admin-confirmed company creation (spec §36). Only fields the admin submits (prefilled from
    what the source established) are stored — nothing is fabricated."""
    name = (fields.get("name") or "").strip()
    if not name:
        raise _unprocessable("Company name is required.")
    repo = CompanyRepository(db)
    existing = await repo.get_by_name(name)
    if existing is not None:
        company = existing
    else:
        company = Company(
            name=name,
            slug=await repo.generate_unique_slug(name),
            website_url=fields.get("website_url"),
            career_url=fields.get("career_url"),
            industry=fields.get("industry"),
            country=fields.get("country"),
            headquarters=fields.get("headquarters"),
            created_by_admin_id=admin_id,
        )
        db.add(company)
        await db.flush()
        audit_service.add(db, admin_id=admin_id, action="create", entity_type="company", entity_id=company.id, metadata={"from_discovered_item": item.id})
    item.company_id = company.id
    return company


# ------------------------------------------------------------------------------------------------
# Change application
# ------------------------------------------------------------------------------------------------

async def record_change(
    db: AsyncSession, *, entity_type: str, entity_id: str, field: str, old, new, source_id: str | None, item_id: str | None
) -> ContentChange | None:
    """Idempotent: an identical pending change isn't recorded twice across runs."""
    pending = (
        await db.execute(
            select(ContentChange).where(
                ContentChange.entity_type == entity_type, ContentChange.entity_id == entity_id,
                ContentChange.field == field, ContentChange.status == ChangeStatus.PENDING,
            )
        )
    ).scalars().all()
    for change in pending:
        if change.new_value_json.get("value") == new:
            return None
        # A newer value supersedes an older pending one for the same field.
        change.status = ChangeStatus.DISMISSED
        change.resolved_at = _now()
    change = ContentChange(
        entity_type=entity_type, entity_id=entity_id, field=field, old_value_json={"value": old}, new_value_json={"value": new},
        source_id=source_id, discovered_item_id=item_id, status=ChangeStatus.PENDING, detected_at=_now(),
    )
    db.add(change)
    return change


async def apply_change(db: AsyncSession, change: ContentChange, *, admin_id: str | None) -> None:
    entity = await load_entity(db, change.entity_type, change.entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The record this change belongs to no longer exists.")
    new_value = change.new_value_json.get("value")
    if change.field == "source_state":
        entity.source_state = SourceState(new_value)
        if entity.source_state in (SourceState.SOURCE_REMOVED, SourceState.CLOSED, SourceState.EXPIRED) and entity.status == ContentStatus.PUBLISHED:
            # Confirmed at the source: stop presenting it as active; never delete (saved items,
            # applications and CV analyses still reference it).
            entity.status = ContentStatus.EXPIRED
            audit_service.add(db, admin_id=admin_id, action="content_expired", entity_type=change.entity_type.lower(), entity_id=entity.id, metadata={"reason": new_value})
    else:
        setattr(entity, change.field, coerce_for_field(change.entity_type, change.field, new_value))
        if change.field == "application_deadline" and change.entity_type == ENTITY_JOB and getattr(entity, "expires_at", None) is not None:
            entity.expires_at = coerce_for_field(change.entity_type, "expires_at", new_value)
    if hasattr(entity, "last_verified_at"):
        entity.last_verified_at = _now()
    change.status = ChangeStatus.APPLIED
    change.resolved_at = _now()
    change.resolved_by_admin_id = admin_id
    action = "deadline_changed" if change.field == "application_deadline" else "opportunity_updated_from_source"
    audit_service.add(
        db, admin_id=admin_id, action=action, entity_type=change.entity_type.lower(), entity_id=change.entity_id,
        metadata={"field": change.field, "change_id": change.id},
    )


async def dismiss_change(db: AsyncSession, change: ContentChange, *, admin_id: str | None) -> None:
    if change.field == "source_state":
        entity = await load_entity(db, change.entity_type, change.entity_id)
        if entity is not None and entity.source_state != SourceState.ACTIVE:
            entity.source_state = SourceState(change.old_value_json.get("value") or "ACTIVE")
    change.status = ChangeStatus.DISMISSED
    change.resolved_at = _now()
    change.resolved_by_admin_id = admin_id


# ------------------------------------------------------------------------------------------------
# Follower notifications (spec §47-48)
# ------------------------------------------------------------------------------------------------

_PREFERENCE_FOR_ENTITY = {ENTITY_JOB: "job_matches", ENTITY_SCHOLARSHIP: "scholarships", ENTITY_INTELLIGENCE: "company_intelligence"}
MAX_NOTIFIED_FOLLOWERS = 1000


async def notify_company_followers(db: AsyncSession, entity_type: str, entity, *, provider: PushProvider | None = None) -> int:
    """Push "new from a company you follow" through the existing push infrastructure, respecting each
    user's notification preferences. Deep links point at the real entity route. Returns the number
    of devices sent to (the mock provider in environments without FCM/APNs credentials)."""
    company_id = getattr(entity, "company_id", None)
    if not company_id or entity.status != ContentStatus.PUBLISHED:
        return 0
    company = await db.get(Company, company_id)
    if company is None:
        return 0
    follower_ids = (await db.execute(select(CompanyFollow.user_id).where(CompanyFollow.company_id == company_id).limit(MAX_NOTIFIED_FOLLOWERS))).scalars().all()
    if not follower_ids:
        return 0
    preference = _PREFERENCE_FOR_ENTITY[entity_type]
    opted_out = set(
        (await db.execute(select(NotificationPreferences.user_id).where(
            NotificationPreferences.user_id.in_(follower_ids), getattr(NotificationPreferences, preference).is_(False)
        ))).scalars().all()
    )
    tokens = (await db.execute(select(DeviceToken).where(DeviceToken.user_id.in_(set(follower_ids) - opted_out), DeviceToken.is_active.is_(True)))).scalars().all()
    if entity_type == ENTITY_JOB:
        title, route = f"New at {company.name}", f"/jobs/{entity.slug}"
        body = entity.title
    else:
        title, route = f"{company.name} update", f"/intelligence/{entity.slug}"
        body = entity.headline
    provider = provider or MockPushProvider()
    sent = 0
    for token in tokens:
        try:
            if await provider.send(token=token.token, title=title, body=body[:180], data={"route": route, "entity_type": entity_type, "entity_id": entity.id}):
                sent += 1
        except Exception:  # noqa: BLE001 — one bad device must not stop the others
            logger.warning("follower push failed for one device")
    return sent

