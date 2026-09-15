"""Admin-facing discovery operations: source registry + health, the discovery queue, side-by-side
review, draft/publish, change history decisions and operational metrics (spec §32-35, §60-62)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.ingestion.adapters.registry import (
    DEFAULT_CRAWL_INTERVAL_MINUTES,
    DEFAULT_DISCOVERY_METHOD,
    DEFAULT_TRUST_LEVEL,
    adapter_enabled,
    adapter_for,
)
from app.ingestion.http_client import DiscoveryHttpClient
from app.ingestion.text import normalize_title
from app.ingestion.url_safety import host_of
from app.models.admin_ops import (
    AuditLog,
    ChangeStatus,
    ContentChange,
    ContentSource,
    DiscoveredItem,
    DiscoveredItemStatus,
    DiscoveredItemType,
    DiscoveryMethod,
    DiscoveryRun,
    DiscoveryRunStatus,
    DiscoveryRunType,
    ItemVerificationStatus,
    VerificationStatus,
)
from app.models.company import Company
from app.models.job import LISTED_SOURCE_STATES, ContentStatus, Job, SourceState
from app.models.scholarship import Scholarship
from app.schemas.admin_ops import (
    CompanyProposalIn,
    ContentChangeOut,
    ContentSourceCreate,
    ContentSourceOut,
    ContentSourceUpdate,
    DiscoveredItemCreate,
    DiscoveredItemOut,
    DiscoveryDraftIn,
    DiscoveryMetricsOut,
    DiscoveryReviewOut,
    SourceHealthOut,
    SourceTestOut,
)
from app.services import audit_service
from app.services.discovery import publishing
from app.services.discovery.pipeline import snapshot_of
from app.services.discovery.records import ENTITY_INTELLIGENCE, ENTITY_JOB, ENTITY_SCHOLARSHIP, entity_type_for

QUEUE_DEFAULT_STATUSES = (DiscoveredItemStatus.NEW, DiscoveredItemStatus.NEEDS_REVIEW, DiscoveredItemStatus.VERIFIED)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def source_health(source: ContentSource, last_run_status: DiscoveryRunStatus | None) -> str:
    """HEALTHY / DEGRADED / FAILING / PAUSED / UNKNOWN for the source registry and dashboard."""
    if not source.is_active:
        return "PAUSED"
    if source.last_checked_at is None:
        return "UNKNOWN"
    if (source.consecutive_failures or 0) >= 3 or source.verification_status == VerificationStatus.FAILING:
        return "FAILING"
    if (source.consecutive_failures or 0) > 0 or last_run_status in (DiscoveryRunStatus.PARTIAL, DiscoveryRunStatus.RATE_LIMITED, DiscoveryRunStatus.FAILED):
        return "DEGRADED"
    return "HEALTHY"


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


class ContentSourceService:
    def __init__(self, db: AsyncSession, *, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def list_all(self) -> list[ContentSource]:
        return list((await self.db.execute(select(ContentSource).order_by(ContentSource.created_at.desc()))).scalars().all())

    async def get_or_404(self, source_id: str) -> ContentSource:
        source = await self.db.get(ContentSource, source_id)
        if source is None:
            raise _not_found("Source")
        return source

    async def _check_company(self, company_id: str | None) -> None:
        if company_id and await self.db.get(Company, company_id) is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown company_id")

    async def create(self, payload: ContentSourceCreate, *, admin_id: str | None) -> ContentSource:
        await self._check_company(payload.company_id)
        data = payload.model_dump()
        source_type = payload.source_type.value
        data["trust_level"] = data["trust_level"] or DEFAULT_TRUST_LEVEL.get(source_type, 1)
        data["discovery_method"] = data["discovery_method"] or DiscoveryMethod(DEFAULT_DISCOVERY_METHOD.get(source_type, "MANUAL"))
        data["crawl_interval_minutes"] = data["crawl_interval_minutes"] or DEFAULT_CRAWL_INTERVAL_MINUTES.get(source_type, 1440)
        source = ContentSource(created_by_admin_id=admin_id, domain=host_of(payload.url), **data)
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def update(self, source_id: str, payload: ContentSourceUpdate) -> tuple[ContentSource, list[str]]:
        source = await self.get_or_404(source_id)
        changes = payload.model_dump(exclude_unset=True)
        await self._check_company(changes.get("company_id"))
        for field, value in changes.items():
            if value is None and field in ("trust_level", "discovery_method", "content_types", "adapter_config_json", "is_active", "polling_enabled", "crawl_interval_minutes", "auto_publish_allowed", "verification_status"):
                continue  # these columns are NOT NULL; omitting a value means "unchanged"
            setattr(source, field, value)
        if "url" in changes and changes["url"]:
            source.domain = host_of(changes["url"])
        if changes.get("is_active") or changes.get("polling_enabled"):
            source.next_poll_after = None  # an admin resuming a source lifts any backoff
        await self.db.commit()
        await self.db.refresh(source)
        return source, sorted(changes)

    async def delete(self, source_id: str) -> None:
        source = await self.get_or_404(source_id)
        await self.db.delete(source)
        await self.db.commit()

    async def health(self) -> list[SourceHealthOut]:
        sources = await self.list_all()
        latest = (
            select(DiscoveryRun.source_id, func.max(DiscoveryRun.queued_at).label("queued_at"))
            .where(DiscoveryRun.run_type == DiscoveryRunType.SOURCE_DISCOVERY).group_by(DiscoveryRun.source_id).subquery()
        )
        last_runs = {
            run.source_id: run
            for run in (await self.db.execute(
                select(DiscoveryRun).join(latest, (DiscoveryRun.source_id == latest.c.source_id) & (DiscoveryRun.queued_at == latest.c.queued_at))
            )).scalars()
        }
        company_names = dict((await self.db.execute(
            select(Company.id, Company.name).where(Company.id.in_({s.company_id for s in sources if s.company_id}))
        )).all()) if any(s.company_id for s in sources) else {}
        counts = dict((await self.db.execute(select(DiscoveredItem.source_id, func.count()).group_by(DiscoveredItem.source_id))).all())
        awaiting = dict((await self.db.execute(
            select(DiscoveredItem.source_id, func.count()).where(DiscoveredItem.status.in_(QUEUE_DEFAULT_STATUSES)).group_by(DiscoveredItem.source_id)
        )).all())
        published = dict((await self.db.execute(
            select(DiscoveredItem.source_id, func.count()).where(DiscoveredItem.status == DiscoveredItemStatus.PUBLISHED).group_by(DiscoveredItem.source_id)
        )).all())
        out = []
        for source in sources:
            last_run = last_runs.get(source.id)
            adapter = adapter_for(snapshot_of(source, None))
            data = ContentSourceOut.model_validate(source).model_dump()
            data.pop("requires_review", None)
            out.append(SourceHealthOut(
                **data,
                items_discovered=counts.get(source.id, 0),
                items_awaiting_review=awaiting.get(source.id, 0),
                items_published=published.get(source.id, 0),
                last_run_status=last_run.status if last_run else None,
                last_run_at=(last_run.finished_at or last_run.queued_at) if last_run else None,
                last_run_new=last_run.items_new if last_run else None,
                last_run_updated=last_run.items_updated if last_run else None,
                last_run_duplicates=last_run.items_duplicate if last_run else None,
                last_run_removed=last_run.items_removed if last_run else None,
                adapter_available=adapter is not None and adapter_enabled(adapter, self.settings),
                adapter_name=adapter.name if adapter else None,
                company_name=company_names.get(source.company_id),
                health=source_health(source, last_run.status if last_run else None),
            ))
        return out

    async def test_connection(self, source_id: str, *, http_client_factory=None) -> SourceTestOut:
        """A bounded live fetch through the source's adapter. Nothing is stored."""
        source = await self.get_or_404(source_id)
        company = await self.db.get(Company, source.company_id) if source.company_id else None
        snapshot = snapshot_of(source, company)
        adapter = adapter_for(snapshot)
        if adapter is None:
            return SourceTestOut(ok=False, error_code="NO_ADAPTER", error="This source is tracked manually; there is nothing to fetch.")
        s = self.settings
        client = http_client_factory() if http_client_factory else DiscoveryHttpClient(
            user_agent=s.discovery_user_agent, timeout_seconds=s.discovery_request_timeout_seconds,
            max_response_bytes=s.discovery_max_response_bytes, max_requests=15,
            min_interval_seconds=s.discovery_min_request_interval_seconds, use_system_trust_store=s.outbound_tls_trust_store == "system",
        )
        try:
            check = await adapter.health_check(snapshot, client, max_items=5)
        finally:
            await client.aclose()
        return SourceTestOut(
            ok=check.ok, adapter=adapter.name, found=check.found, complete=check.complete, sample_titles=[t for t in check.sample_titles if t],
            warnings=check.warnings, error_code=check.error_code, error=check.error, http_status=client.stats.get("last_status"),
            requests=client.stats.get("requests", 0),
        )

    async def runs(self, source_id: str, *, limit: int = 20) -> list[DiscoveryRun]:
        await self.get_or_404(source_id)
        return list((await self.db.execute(
            select(DiscoveryRun).where(DiscoveryRun.source_id == source_id).order_by(DiscoveryRun.queued_at.desc()).limit(limit)
        )).scalars().all())


class DiscoveryService:
    """Nothing here publishes without an explicit admin action (or, for auto-publish, every gate in
    `publishing.auto_publish_gates` passing in the pipeline)."""

    def __init__(self, db: AsyncSession, *, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def get_or_404(self, item_id: str) -> DiscoveredItem:
        item = await self.db.get(DiscoveredItem, item_id)
        if item is None:
            raise _not_found("Discovered item")
        return item

    async def _pending_counts(self, items: list[DiscoveredItem]) -> dict[str, int]:
        ids = [i.id for i in items]
        if not ids:
            return {}
        return dict((await self.db.execute(
            select(ContentChange.discovered_item_id, func.count()).where(ContentChange.discovered_item_id.in_(ids), ContentChange.status == ChangeStatus.PENDING).group_by(ContentChange.discovered_item_id)
        )).all())

    async def to_out(self, items: list[DiscoveredItem]) -> list[DiscoveredItemOut]:
        pending = await self._pending_counts(items)
        source_ids = {i.source_id for i in items}
        names = dict((await self.db.execute(select(ContentSource.id, ContentSource.name).where(ContentSource.id.in_(source_ids)))).all()) if source_ids else {}
        out = []
        for item in items:
            model = DiscoveredItemOut.model_validate(item)
            model.pending_changes = pending.get(item.id, 0)
            model.source_name = names.get(item.source_id)
            model.flags = list((item.evidence_json or {}).get("flags") or [])
            out.append(model)
        return out

    async def list_admin(
        self,
        *,
        page: int,
        page_size: int,
        item_type: DiscoveredItemType | None = None,
        item_status: DiscoveredItemStatus | None = None,
        source_id: str | None = None,
        company_id: str | None = None,
        country: str | None = None,
        min_trust: int | None = None,
        duplicates: str | None = None,  # "only" | "exclude"
        discovered_after: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[DiscoveredItemOut], int]:
        conditions = []
        if item_type:
            conditions.append(DiscoveredItem.item_type == item_type)
        if item_status:
            conditions.append(DiscoveredItem.status == item_status)
        elif duplicates != "only":
            conditions.append(DiscoveredItem.status.in_(QUEUE_DEFAULT_STATUSES))
        if duplicates == "only":
            conditions.append(or_(DiscoveredItem.status == DiscoveredItemStatus.DUPLICATE, DiscoveredItem.duplicate_of_id.isnot(None)))
        elif duplicates == "exclude":
            conditions.append(DiscoveredItem.duplicate_of_id.is_(None))
        if source_id:
            conditions.append(DiscoveredItem.source_id == source_id)
        if company_id:
            conditions.append(DiscoveredItem.company_id == company_id)
        if country:
            conditions.append(func.lower(DiscoveredItem.country) == country.lower())
        if min_trust:
            conditions.append(DiscoveredItem.trust_level >= min_trust)
        if discovered_after:
            conditions.append(DiscoveredItem.created_at >= discovered_after)
        if search:
            conditions.append(DiscoveredItem.normalized_title.like(f"%{normalize_title(search)}%"))
        total = (await self.db.execute(select(func.count()).select_from(DiscoveredItem).where(*conditions))).scalar_one()
        rows = (await self.db.execute(
            select(DiscoveredItem).where(*conditions).order_by(DiscoveredItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return await self.to_out(list(rows)), total

    async def ingest(self, payload: DiscoveredItemCreate) -> DiscoveredItem | None:
        """Manual entry point. Returns None for a duplicate of an already-tracked item."""
        source = await self.db.get(ContentSource, payload.source_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown source_id")
        from app.ingestion.url_safety import canonicalize_url

        normalized = normalize_title(payload.detected_title)
        canonical = canonicalize_url(payload.original_url)
        conditions = [DiscoveredItem.canonical_url == canonical, DiscoveredItem.original_url == payload.original_url]
        if payload.external_id:
            conditions.append((DiscoveredItem.source_id == payload.source_id) & (DiscoveredItem.external_id == payload.external_id))
        conditions.append((DiscoveredItem.source_id == payload.source_id) & (DiscoveredItem.normalized_title == normalized))
        if (await self.db.execute(select(DiscoveredItem.id).where(or_(*conditions)).limit(1))).scalar_one_or_none():
            return None
        item = DiscoveredItem(
            source_id=payload.source_id, item_type=payload.item_type, external_id=payload.external_id,
            detected_title=payload.detected_title, detected_company_name=payload.detected_company_name,
            original_url=payload.original_url, canonical_url=canonical, raw_payload_json=payload.raw_payload,
            normalized_title=normalized, discovery_method=DiscoveryMethod.MANUAL, trust_level=source.trust_level,
            verification_status=ItemVerificationStatus.MANUAL_REVIEW_REQUIRED, status=DiscoveredItemStatus.NEEDS_REVIEW,
            evidence_json={"source_quality": "Manually reported", "flags": [], "checks": ["reported by an editor; facts must be confirmed at the source"]},
            last_seen_at=_now(),
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def _decide(self, item_id: str, new_status: DiscoveredItemStatus, admin_id: str | None) -> DiscoveredItem:
        item = await self.get_or_404(item_id)
        item.status = new_status
        item.reviewed_by_admin_id = admin_id
        item.reviewed_at = _now()
        await self.db.commit()
        return item

    async def ignore(self, item_id: str, *, admin_id: str | None) -> DiscoveredItem:
        return await self._decide(item_id, DiscoveredItemStatus.IGNORED, admin_id)

    async def reject(self, item_id: str, *, admin_id: str | None) -> DiscoveredItem:
        return await self._decide(item_id, DiscoveredItemStatus.REJECTED, admin_id)

    # ------------------------------------------------------------------------------------------
    @staticmethod
    def overrides_for(item: DiscoveredItem, payload: DiscoveryDraftIn) -> dict:
        kind = entity_type_for(item.item_type)
        title_key = {ENTITY_JOB: "title", ENTITY_SCHOLARSHIP: "name", ENTITY_INTELLIGENCE: "headline"}[kind]
        overrides = {title_key: payload.title, "summary": payload.summary, "description": payload.description, "country": payload.country}
        if kind == ENTITY_JOB:
            overrides.update({"location": payload.location, "application_url": payload.application_url, "application_deadline": payload.deadline})
        elif kind == ENTITY_SCHOLARSHIP:
            overrides.update({"official_application_url": payload.application_url, "deadline": payload.deadline})
        else:
            overrides.update({"category": payload.category, "career_relevance": payload.career_relevance})
            overrides.pop("description")
        return {k: v for k, v in overrides.items() if v is not None}

    def _extracted_or_minimal(self, item: DiscoveredItem) -> None:
        """Manually reported items have no extracted record yet; seed one from what was reported."""
        if item.extracted_data_json:
            return
        kind = entity_type_for(item.item_type)
        title_key = {ENTITY_JOB: "title", ENTITY_SCHOLARSHIP: "name", ENTITY_INTELLIGENCE: "headline"}[kind]
        org_key = "provider" if kind == ENTITY_SCHOLARSHIP else "company"
        item.extracted_data_json = {
            "content_type": item.item_type.value, title_key: item.detected_title, org_key: item.detected_company_name,
            "source_url": item.original_url, "confidence": 0.3,
        }

    async def create_draft(self, item_id: str, payload: DiscoveryDraftIn, *, admin_id: str | None) -> dict:
        item = await self.get_or_404(item_id)
        if item.status in (DiscoveredItemStatus.DRAFT_CREATED, DiscoveredItemStatus.PUBLISHED) or item.created_draft_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item has already been reviewed.")
        if item.status in (DiscoveredItemStatus.IGNORED, DiscoveredItemStatus.REJECTED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item was dismissed.")
        self._extracted_or_minimal(item)
        entity_type, entity = await publishing.materialize_item(
            self.db, item, publish=False, admin_id=admin_id, overrides=self.overrides_for(item, payload), company_id=payload.company_id,
        )
        await self.db.commit()
        return {"item_type": item.item_type.value, "entity_type": entity_type, "draft_id": entity.id}

    async def publish(self, item_id: str, payload: DiscoveryDraftIn, *, admin_id: str | None) -> dict:
        item = await self.get_or_404(item_id)
        if item.status in (DiscoveredItemStatus.IGNORED, DiscoveredItemStatus.REJECTED, DiscoveredItemStatus.PUBLISHED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item can't be published in its current state.")
        blockers = self.publish_blockers(item)
        if blockers:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=blockers[0])
        self._extracted_or_minimal(item)
        entity_type, entity = await publishing.materialize_item(
            self.db, item, publish=True, admin_id=admin_id, overrides=self.overrides_for(item, payload), company_id=payload.company_id,
        )
        await self.db.commit()
        notified = await publishing.notify_company_followers(self.db, entity_type, entity)
        return {"item_type": item.item_type.value, "entity_type": entity_type, "entity_id": entity.id, "slug": entity.slug, "notified_devices": notified}

    @staticmethod
    def publish_blockers(item: DiscoveredItem) -> list[str]:
        blockers = []
        evidence = item.evidence_json or {}
        if item.matched_entity_id and not item.created_draft_id:
            blockers.append("This listing already exists in CareerOS — review its detected changes instead of publishing a copy.")
        if item.status == DiscoveredItemStatus.DUPLICATE:
            blockers.append("This item is a duplicate of another discovered item.")
        if item.status == DiscoveredItemStatus.SOURCE_REMOVED:
            blockers.append("The listing is no longer at its source.")
        if "DISCOVERY_ONLY_SOURCE" in (evidence.get("flags") or []):
            blockers.append("Discovery-only source: locate the official listing and set its URL before publishing.")
        return blockers

    async def create_company(self, item_id: str, payload: CompanyProposalIn, *, admin_id: str | None) -> Company:
        item = await self.get_or_404(item_id)
        company = await publishing.create_company_from_proposal(self.db, item, admin_id=admin_id, fields=payload.model_dump())
        await self.db.commit()
        await self.db.refresh(company)
        return company

    # ------------------------------------------------------------------------------------------
    async def review(self, item_id: str) -> DiscoveryReviewOut:
        item = await self.get_or_404(item_id)
        source = await self.db.get(ContentSource, item.source_id)
        entity_type, entity = await publishing.linked_entity(self.db, item)
        current = None
        if entity is not None:
            current = {
                "entity_type": entity_type,
                "id": entity.id,
                "status": entity.status.value,
                "source_state": getattr(entity, "source_state", None).value if getattr(entity, "source_state", None) is not None else None,
                **{f: _plain(getattr(entity, f, None)) for f in _REVIEW_FIELDS[entity_type]},
            }
        changes = await self.changes(entity_type=entity_type, entity_id=entity.id) if entity is not None else []
        duplicate = await self.db.get(DiscoveredItem, item.duplicate_of_id) if item.duplicate_of_id else None
        blockers = self.publish_blockers(item)
        item_out = (await self.to_out([item]))[0]
        return DiscoveryReviewOut(
            item=item_out,
            source=ContentSourceOut.model_validate(source),
            evidence=item.evidence_json or {},
            extracted=item.extracted_data_json or {},
            raw_payload=item.raw_payload_json or {},
            current_record=current,
            pending_changes=[c for c in changes if c.status == ChangeStatus.PENDING],
            duplicate_of=(await self.to_out([duplicate]))[0] if duplicate else None,
            can_publish=not blockers and item.status not in (DiscoveredItemStatus.IGNORED, DiscoveredItemStatus.REJECTED, DiscoveredItemStatus.PUBLISHED),
            publish_blockers=blockers,
        )

    async def changes(self, *, entity_type: str | None = None, entity_id: str | None = None, change_status: ChangeStatus | None = None, limit: int = 100) -> list[ContentChangeOut]:
        query = select(ContentChange)
        if entity_type:
            query = query.where(ContentChange.entity_type == entity_type)
        if entity_id:
            query = query.where(ContentChange.entity_id == entity_id)
        if change_status:
            query = query.where(ContentChange.status == change_status)
        rows = (await self.db.execute(query.order_by(ContentChange.detected_at.desc()).limit(limit))).scalars().all()
        return [_change_out(c) for c in rows]

    async def decide_change(self, change_id: str, *, apply: bool, admin_id: str | None) -> ContentChangeOut:
        change = await self.db.get(ContentChange, change_id)
        if change is None:
            raise _not_found("Change")
        if change.status != ChangeStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This change was already resolved.")
        if apply:
            await publishing.apply_change(self.db, change, admin_id=admin_id)
        else:
            await publishing.dismiss_change(self.db, change, admin_id=admin_id)
        await self._settle_item(change.discovered_item_id)
        await self.db.commit()
        return _change_out(change)

    async def decide_source_state(self, entity_type: str, entity_id: str, *, confirm: bool, admin_id: str | None) -> dict:
        """Confirm (expire, keep for history) or dismiss a detected removal/closure (spec §67)."""
        entity = await publishing.load_entity(self.db, entity_type, entity_id)
        if entity is None or not hasattr(entity, "source_state"):
            raise _not_found("Record")
        pending = (await self.db.execute(
            select(ContentChange).where(ContentChange.entity_type == entity_type, ContentChange.entity_id == entity_id, ContentChange.field == "source_state", ContentChange.status == ChangeStatus.PENDING)
        )).scalars().all()
        if not pending and entity.source_state == SourceState.ACTIVE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There is no pending source-state change for this record.")
        for change in pending:
            if confirm:
                await publishing.apply_change(self.db, change, admin_id=admin_id)
            else:
                await publishing.dismiss_change(self.db, change, admin_id=admin_id)
        if confirm and not pending and entity.status == ContentStatus.PUBLISHED:
            entity.status = ContentStatus.EXPIRED
            audit_service.add(self.db, admin_id=admin_id, action="content_expired", entity_type=entity_type.lower(), entity_id=entity.id, metadata={"reason": entity.source_state.value})
        if not confirm:
            entity.source_state = SourceState.ACTIVE
            entity.last_verified_at = _now()
        await self.db.commit()
        return {"entity_type": entity_type, "entity_id": entity.id, "status": entity.status.value, "source_state": entity.source_state.value}

    async def _settle_item(self, item_id: str | None) -> None:
        if not item_id:
            return
        item = await self.db.get(DiscoveredItem, item_id)
        if item is None or item.status != DiscoveredItemStatus.NEEDS_REVIEW or not item.matched_entity_id:
            return
        remaining = (await self.db.execute(
            select(func.count()).select_from(ContentChange).where(ContentChange.discovered_item_id == item_id, ContentChange.status == ChangeStatus.PENDING)
        )).scalar_one()
        if remaining == 0:
            item.status = DiscoveredItemStatus.DUPLICATE if not item.created_draft_id else DiscoveredItemStatus.PUBLISHED

    # ------------------------------------------------------------------------------------------
    async def metrics(self) -> DiscoveryMetricsOut:
        s = self.settings
        day_ago, week_ago = _now() - timedelta(days=1), _now() - timedelta(days=7)

        async def count(model, *conditions) -> int:
            return (await self.db.execute(select(func.count()).select_from(model).where(*conditions))).scalar_one()

        runs_24h = (await self.db.execute(select(DiscoveryRun).where(DiscoveryRun.queued_at >= day_ago, DiscoveryRun.run_type == DiscoveryRunType.SOURCE_DISCOVERY))).scalars().all()
        durations = [r.duration_ms for r in runs_24h if r.duration_ms is not None]
        expired_actions = await count(AuditLog, AuditLog.action == "content_expired", AuditLog.created_at >= week_ago)
        sources = await ContentSourceService(self.db, settings=s).list_all()
        latest_status = dict((await self.db.execute(
            select(DiscoveryRun.source_id, DiscoveryRun.status)
            .join(
                select(DiscoveryRun.source_id.label("sid"), func.max(DiscoveryRun.queued_at).label("q"))
                .where(DiscoveryRun.run_type == DiscoveryRunType.SOURCE_DISCOVERY).group_by(DiscoveryRun.source_id).subquery(),
                (DiscoveryRun.source_id == literal_column("sid")) & (DiscoveryRun.queued_at == literal_column("q")),
            )
        )).all())
        readiness: dict[str, int] = {}
        for source in sources:
            readiness[source.readiness.value] = readiness.get(source.readiness.value, 0) + 1
        listed = (Job.status == ContentStatus.PUBLISHED, Job.is_active.is_(True), Job.source_state.in_(LISTED_SOURCE_STATES))
        by_country = (await self.db.execute(
            select(Job.country, func.count()).where(*listed, Job.country.isnot(None)).group_by(Job.country).order_by(func.count().desc()).limit(12)
        )).all()
        industry = func.coalesce(Job.industry, Company.industry)
        by_industry = (await self.db.execute(
            select(industry, func.count()).join(Company, Company.id == Job.company_id).where(*listed, industry.isnot(None))
            .group_by(industry).order_by(func.count().desc()).limit(12)
        )).all()
        finished = [r.finished_at or r.queued_at for r in runs_24h]
        return DiscoveryMetricsOut(
            healthy_sources=sum(1 for src in sources if source_health(src, latest_status.get(src.id)) == "HEALTHY"),
            sources_by_readiness=readiness,
            last_run_at=max(finished) if finished else None,
            items_new_24h=sum(r.items_new for r in runs_24h),
            items_updated_24h=sum(r.items_updated for r in runs_24h),
            possibly_removed=await count(Job, Job.source_state == SourceState.POSSIBLY_REMOVED, Job.status == ContentStatus.PUBLISHED),
            jobs_by_country=[{"country": c, "count": n} for c, n in by_country],
            jobs_by_industry=[{"industry": i, "count": n} for i, n in by_industry],
            active_sources=await count(ContentSource, ContentSource.is_active.is_(True)),
            polling_sources=await count(ContentSource, ContentSource.is_active.is_(True), ContentSource.polling_enabled.is_(True)),
            failing_sources=await count(ContentSource, ContentSource.consecutive_failures >= 3),
            discovery_runs_24h=len(runs_24h),
            failed_runs_24h=sum(1 for r in runs_24h if r.status in (DiscoveryRunStatus.FAILED, DiscoveryRunStatus.RATE_LIMITED)),
            items_found_24h=sum(r.items_found for r in runs_24h),
            items_verified=await count(DiscoveredItem, DiscoveredItem.verification_status == ItemVerificationStatus.SOURCE_VERIFIED, DiscoveredItem.status.in_(QUEUE_DEFAULT_STATUSES)),
            duplicates_24h=sum(r.items_duplicate for r in runs_24h),
            awaiting_review=await count(DiscoveredItem, DiscoveredItem.status.in_(QUEUE_DEFAULT_STATUSES)),
            pending_changes=await count(ContentChange, ContentChange.status == ChangeStatus.PENDING),
            opportunities_expired_7d=expired_actions,
            source_removed_pending=await count(Job, Job.source_state.in_([SourceState.SOURCE_REMOVED, SourceState.UNKNOWN_REQUIRES_REVIEW, SourceState.CLOSED]), Job.status == ContentStatus.PUBLISHED)
            + await count(Scholarship, Scholarship.source_state.in_([SourceState.SOURCE_REMOVED, SourceState.UNKNOWN_REQUIRES_REVIEW, SourceState.CLOSED]), Scholarship.status == ContentStatus.PUBLISHED),
            average_run_ms_24h=int(sum(durations) / len(durations)) if durations else None,
            auto_publish_enabled=s.auto_publish_discovery,
            ai_research_available=s.anthropic_research_available,
            flags={
                "web_discovery": s.web_discovery_enabled, "lever": s.lever_discovery_enabled, "greenhouse": s.greenhouse_discovery_enabled,
                "ashby": s.ashby_discovery_enabled, "smartrecruiters": s.smartrecruiters_discovery_enabled, "workday": s.workday_discovery_enabled,
                "oracle_recruiting": s.oracle_recruiting_discovery_enabled, "structured_ats": s.structured_ats_sync_enabled,
                "html_sources": s.html_source_sync_enabled, "removal_confirmations": s.discovery_removal_confirmations,
                "rss": s.rss_discovery_enabled, "structured_pages": s.structured_page_discovery_enabled, "ai_research": s.ai_research_enabled,
                "anthropic_research": s.anthropic_research_enabled,
            },
        )


_REVIEW_FIELDS = {
    ENTITY_JOB: ("title", "location", "country", "application_deadline", "application_url", "source_url", "short_summary", "requirements", "opportunity_type", "company_id"),
    ENTITY_SCHOLARSHIP: ("name", "organization", "country", "application_deadline", "official_url", "source_url", "summary", "funding_type", "award_type"),
    ENTITY_INTELLIGENCE: ("headline", "category", "summary", "source_url", "source_published_at", "company_id"),
}


def _change_out(change: ContentChange) -> ContentChangeOut:
    return ContentChangeOut(
        id=change.id, entity_type=change.entity_type, entity_id=change.entity_id, field=change.field,
        old_value=(change.old_value_json or {}).get("value"), new_value=(change.new_value_json or {}).get("value"),
        source_id=change.source_id, discovered_item_id=change.discovered_item_id, status=change.status,
        detected_at=change.detected_at, resolved_at=change.resolved_at,
    )


def _plain(value):
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()
    if hasattr(value, "value"):
        return value.value
    return value

