"""One discovery run for one source (spec §0):

    fetch (adapter) → validate → classify → match organization → deduplicate → compare with the
    existing record → discovery queue (or, only if every gate passes, auto-publish) → removal
    detection → source health + run metrics + audit

Web discovery never publishes by default. The run commits once per listing batch, so a failure part
way through keeps what was already verified and records the error on the run and the source.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.ingestion.adapters.base import AdapterConfigurationError, AdapterResult, DiscoveredListing, SourceSnapshot
from app.ingestion.adapters.registry import adapter_enabled, adapter_for
from app.ingestion.http_client import DiscoveryHttpClient, FetchError, RateLimitedError, backoff_until
from app.ingestion.research.anthropic_provider import AnthropicResearchProvider
from app.ingestion.research.providers import ResearchBudget, ResearchOutcome, ResearchProvider, ResearchProviderError, WebResearchProvider
from app.ingestion.schemas import record_canonical_url, record_deadline, record_published_at, record_title
from app.ingestion.url_safety import ATS_DOMAINS, canonicalize_url, is_aggregator_url, is_ats_url, registrable_domain
from app.models.admin_ops import (
    ContentSource,
    DiscoveredItem,
    DiscoveredItemStatus,
    DiscoveredItemType,
    DiscoveryMethod,
    DiscoveryRun,
    DiscoveryRunStatus,
    ItemVerificationStatus,
    ResearchCacheEntry,
    VerificationStatus,
)
from app.models.company import Company
from app.models.job import ContentStatus, Job, SourceState
from app.services import audit_service
from app.services.discovery import publishing
from app.services.discovery.matching import find_duplicates, match_company
from app.services.discovery.records import (
    ENTITY_JOB,
    SOURCE_QUALITY_LABELS,
    diff_record,
    entity_type_for,
    normalized,
    record_hash,
)

logger = logging.getLogger("careeros.discovery.pipeline")

ACTIVE_ITEM_STATUSES = (
    DiscoveredItemStatus.NEW, DiscoveredItemStatus.NEEDS_REVIEW, DiscoveredItemStatus.VERIFIED,
    DiscoveredItemStatus.DRAFT_CREATED, DiscoveredItemStatus.PUBLISHED,
)
# A complete fetch that suddenly returns nothing while this many listings were active is treated as
# a source-side glitch, not as every listing being withdrawn at once.
EMPTY_RESULT_REMOVAL_GUARD = 3
MAX_RATE_LIMIT_BACKOFF = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def snapshot_of(source: ContentSource, company: Company | None) -> SourceSnapshot:
    return SourceSnapshot(
        id=source.id,
        name=source.name,
        organization=source.organization,
        url=source.url,
        source_type=source.source_type.value,
        discovery_method=source.discovery_method.value if hasattr(source.discovery_method, "value") else str(source.discovery_method),
        content_types=tuple(source.content_types or ()),
        adapter_config=dict(source.adapter_config_json or {}),
        trust_level=source.trust_level,
        company_name=company.name if company else None,
    )


@dataclass
class RunStats:
    found: int = 0
    new: int = 0
    updated: int = 0
    duplicate: int = 0
    invalid: int = 0
    removed: int = 0
    unchanged: int = 0
    auto_published: int = 0
    changes_detected: int = 0
    warnings: list[str] = field(default_factory=list)
    ai: dict = field(default_factory=dict)


class DiscoveryPipeline:
    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        http_client_factory=None,
        research_provider: ResearchProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self._http_client_factory = http_client_factory
        self._research_provider = research_provider

    def _client(self) -> DiscoveryHttpClient:
        if self._http_client_factory is not None:
            return self._http_client_factory()
        s = self.settings
        return DiscoveryHttpClient(
            user_agent=s.discovery_user_agent,
            timeout_seconds=s.discovery_request_timeout_seconds,
            max_response_bytes=s.discovery_max_response_bytes,
            max_requests=s.discovery_max_requests_per_run,
            min_interval_seconds=s.discovery_min_request_interval_seconds,
        )

    def _research(self) -> ResearchProvider | None:
        if self._research_provider is not None:
            return self._research_provider if self._research_provider.is_available() else None
        if not self.settings.ai_research_enabled:
            return None
        provider = AnthropicResearchProvider(self.settings)
        return provider if provider.is_available() else None

    # ------------------------------------------------------------------------------------------
    async def execute(self, run: DiscoveryRun) -> DiscoveryRun:
        started = time.monotonic()
        run.status = DiscoveryRunStatus.RUNNING
        run.started_at = run.started_at or _now()
        await self.db.commit()

        source = await self.db.get(ContentSource, run.source_id) if run.source_id else None
        if source is None:
            return await self._finish(run, None, DiscoveryRunStatus.FAILED, started, RunStats(), error=("SOURCE_MISSING", "Source no longer exists"))
        if not self.settings.web_discovery_enabled:
            return await self._finish(run, source, DiscoveryRunStatus.SKIPPED, started, RunStats(), error=("DISABLED", "WEB_DISCOVERY_ENABLED is off"), touch_source=False)
        if not source.is_active:
            return await self._finish(run, source, DiscoveryRunStatus.SKIPPED, started, RunStats(), error=("SOURCE_PAUSED", "Source is paused"), touch_source=False)

        company = await self.db.get(Company, source.company_id) if source.company_id else None
        snapshot = snapshot_of(source, company)
        adapter = adapter_for(snapshot)
        if adapter is None:
            return await self._finish(run, source, DiscoveryRunStatus.SKIPPED, started, RunStats(), error=("NO_ADAPTER", "This source is tracked manually"), touch_source=False)
        if not adapter_enabled(adapter, self.settings):
            return await self._finish(run, source, DiscoveryRunStatus.SKIPPED, started, RunStats(), error=("ADAPTER_DISABLED", f"{adapter.name} discovery is disabled"), touch_source=False)

        stats = RunStats()
        client = self._client()
        try:
            try:
                result = await adapter.discover(snapshot, client, max_items=self.settings.discovery_max_items_per_run)
            except AdapterConfigurationError as exc:
                return await self._finish(run, source, DiscoveryRunStatus.FAILED, started, stats, error=(exc.code, str(exc)))
            except RateLimitedError as exc:
                return await self._finish(run, source, DiscoveryRunStatus.RATE_LIMITED, started, stats, error=(exc.code, "Rate limited by the source"), retry_after=exc.retry_after_seconds)
            except FetchError as exc:
                return await self._finish(run, source, DiscoveryRunStatus.FAILED, started, stats, error=(exc.code, str(exc)[:300]))

            if result.unstructured_pages or (snapshot.discovery_method == "AI_RESEARCH" and snapshot.config("search_queries")):
                await self._research_pages(snapshot, client, result, stats)

            stats.found = len(result.listings)
            stats.invalid = result.invalid_count
            stats.warnings.extend(result.warnings)
            for listing in result.listings:
                await self._process_listing(run, source, listing, stats)
                await self.db.commit()

            if result.complete:
                await self._detect_removals(source, result, stats)
                await self.db.commit()
        finally:
            await client.aclose()

        final = DiscoveryRunStatus.PARTIAL if (stats.invalid or stats.warnings) else DiscoveryRunStatus.SUCCEEDED
        run.stats_json = {
            **(run.stats_json or {}),
            "pages": result.pages,
            "http": {k: v for k, v in client.stats.items() if k != "hosts"},
            "filtered": result.filtered_count,
            "invalid_samples": result.invalid[:10],
            "complete_listing": result.complete,
            "unchanged": stats.unchanged,
            "auto_published": stats.auto_published,
            "changes_detected": stats.changes_detected,
            "ai_research": stats.ai,
            "warnings": stats.warnings[:10],
        }
        return await self._finish(run, source, final, started, stats)

    # ------------------------------------------------------------------------------------------
    async def _research_pages(self, snapshot: SourceSnapshot, client: DiscoveryHttpClient, result: AdapterResult, stats: RunStats) -> None:
        provider = self._research()
        budget = ResearchBudget(
            max_items=self.settings.ai_research_max_items_per_run,
            max_tokens=self.settings.ai_research_max_tokens_per_batch,
            min_trust_level=self.settings.ai_research_min_trust_level,
            content_types=frozenset(self.settings.ai_research_content_type_list),
        )
        web = WebResearchProvider(client=client, ai_provider=provider, budget=budget)
        pages = list(result.unstructured_pages)

        queries = snapshot.config("search_queries") or []
        if provider is not None and isinstance(queries, list):
            allowed = sorted({d for d in (registrable_domain(snapshot.url),) if d} | set(ATS_DOMAINS if snapshot.config("allow_ats_domains", True) else ()))
            for query in queries[:5]:
                try:
                    urls, tokens = await provider.discover_candidate_urls(query=str(query)[:200], allowed_domains=allowed)
                except ResearchProviderError as exc:
                    stats.warnings.append(f"research search failed: {exc.code}")
                    continue
                budget.tokens_used += tokens
                pages.extend((url, None) for url in urls if not any(url == p[0] for p in pages))

        if not pages:
            return
        if provider is None:
            stats.warnings.append(f"{len(pages)} page(s) had no structured data; AI research is unavailable — manual review required")
        for page_url, markup in pages[:20]:
            outcome = await self._cached_research(web, snapshot, page_url, markup, provider)
            for record, evidence in zip(outcome.records, outcome.evidence or [{}] * len(outcome.records), strict=False):
                result.listings.append(DiscoveredListing(record=record, raw={"page": page_url}, method="AI_RESEARCH" if outcome.provider not in ("structured", "web") else "STRUCTURED_DATA", evidence=evidence))
            for error in outcome.errors:
                stats.warnings.append(f"research: {error}")
        stats.ai = {"items_used": budget.items_used, "tokens_used": budget.tokens_used, "skipped": budget.skipped, "provider": provider.name if provider else None}

    async def _cached_research(self, web: WebResearchProvider, snapshot: SourceSnapshot, page_url: str, markup: str | None, provider) -> ResearchOutcome:
        """Unchanged pages are never researched twice by a paid provider (spec §75)."""
        from app.ingestion.schemas import parse_record
        from app.ingestion.text import content_hash, html_to_text

        if markup is None or provider is None:
            return await web.research_page(snapshot, page_url, markup)
        page_hash = content_hash(html_to_text(markup, max_length=None) or "")
        cached = (await self.db.execute(
            select(ResearchCacheEntry).where(ResearchCacheEntry.provider == provider.name, ResearchCacheEntry.url == page_url[:1024], ResearchCacheEntry.content_hash == page_hash)
        )).scalar_one_or_none()
        if cached is not None:
            records, evidence = [], []
            for stored, stored_evidence in zip(cached.result_json.get("records", []), cached.result_json.get("evidence", []), strict=False):
                try:
                    records.append(parse_record(stored))
                    evidence.append({**stored_evidence, "cached": True})
                except ValueError:
                    continue
            return ResearchOutcome(records=records, evidence=evidence, provider=provider.name)
        outcome = await web.research_page(snapshot, page_url, markup)
        if outcome.provider == provider.name:
            self.db.add(ResearchCacheEntry(
                provider=provider.name, url=page_url[:1024], content_hash=page_hash, tokens_used=outcome.tokens_used, created_at=_now(),
                result_json={"records": [r.model_dump(mode="json") for r in outcome.records], "evidence": outcome.evidence},
            ))
        return outcome

    # ------------------------------------------------------------------------------------------
    async def _process_listing(self, run: DiscoveryRun, source: ContentSource, listing: DiscoveredListing, stats: RunStats) -> None:
        record = listing.record
        item_type = DiscoveredItemType(record.content_type)
        entity_type = entity_type_for(item_type)
        now = _now()

        company_match = await match_company(self.db, source, record)
        dedup = await find_duplicates(
            self.db, source=source, record=record, company=company_match.company,
            item_types=tuple(t.value for t in DiscoveredItemType if entity_type_for(t) == entity_type),
        )
        verification, checks, flags = self._verify(source, listing)
        record_data = record.model_dump(mode="json")
        digest = record_hash(record)
        canonical_url = canonicalize_url(record_canonical_url(record))

        evidence = {
            "source_quality": SOURCE_QUALITY_LABELS.get(source.source_type.value, source.source_type.value),
            "source_name": source.name,
            "source_type": source.source_type.value,
            "trust_level": source.trust_level,
            "source_ownership_verified": source.verification_status == VerificationStatus.VERIFIED,
            "matched_organization": {"company_id": company_match.company.id, "name": company_match.company.name, "method": company_match.method} if company_match.company else None,
            "proposed_company": company_match.proposal,
            "external_id": record.source_external_id,
            "requisition_id": getattr(record, "requisition_id", None),
            "discovery_method": listing.method,
            "checks": checks,
            "flags": flags + [f for f in listing.evidence.get("flags", []) if f not in flags],
            "injection_suspected": bool(listing.evidence.get("injection_suspected")),
            "dedup": dedup.reasons,
            "verified_at": now.isoformat(),
            **{k: v for k, v in listing.evidence.items() if k in ("api", "feed", "structured_data", "page", "ai_provider", "ai_model", "page_truncated", "dropped_fields", "experimental", "cached")},
        }
        if listing.evidence.get("injection_suspected"):
            evidence["injection_markers"] = listing.evidence.get("injection_markers", [])

        entity = dedup.entity
        item = dedup.same_item
        content_changed = False
        if item is not None:
            item.last_seen_at = now
            item.last_verified_at = now
            item.run_id = run.id
            content_changed = item.content_hash != digest
            if content_changed:
                item.extracted_data_json = record_data
                item.content_hash = digest
                item.detected_title = record_title(record)[:500]
                item.deadline = record_deadline(record)
                item.evidence_json = evidence
                item.verification_status = verification
                item.confidence = record.confidence
            if item.status == DiscoveredItemStatus.SOURCE_REMOVED:
                item.status = DiscoveredItemStatus.NEEDS_REVIEW
            if entity is None and (item.created_draft_id or item.matched_entity_id):
                _, entity = await publishing.linked_entity(self.db, item)
        else:
            if dedup.duplicate_of is not None:
                status_value = DiscoveredItemStatus.DUPLICATE
            elif verification == ItemVerificationStatus.SOURCE_VERIFIED and company_match.company is not None and not evidence["flags"]:
                status_value = DiscoveredItemStatus.VERIFIED
            else:
                status_value = DiscoveredItemStatus.NEEDS_REVIEW
            item = DiscoveredItem(
                source_id=source.id,
                run_id=run.id,
                item_type=item_type,
                external_id=record.source_external_id,
                detected_title=record_title(record)[:500],
                detected_company_name=(company_match.company.name if company_match.company else (getattr(record, "company", None) or getattr(record, "provider", None))),
                company_id=company_match.company.id if company_match.company else None,
                original_url=record.source_url,
                canonical_url=canonical_url,
                location=getattr(record, "location", None),
                country=getattr(record, "country", None),
                published_at=record_published_at(record),
                deadline=record_deadline(record),
                raw_payload_json=listing.raw or {},
                extracted_data_json=record_data,
                evidence_json=evidence,
                normalized_title=normalized(record_title(record))[:500],
                content_hash=digest,
                discovery_method=DiscoveryMethod(listing.method) if listing.method in DiscoveryMethod.__members__ else None,
                verification_status=verification,
                trust_level=source.trust_level,
                confidence=record.confidence,
                duplicate_of_id=dedup.duplicate_of.id if dedup.duplicate_of else None,
                status=status_value,
                last_seen_at=now,
                last_verified_at=now,
            )
            self.db.add(item)
            await self.db.flush()
            if status_value == DiscoveredItemStatus.DUPLICATE:
                stats.duplicate += 1
            elif entity is None:
                stats.new += 1

        if entity is not None:
            item.matched_entity_type = item.matched_entity_type or entity_type
            item.matched_entity_id = item.matched_entity_id or entity.id
            await self._compare_with_record(source, item, entity_type, entity, record, stats)
        elif dedup.same_item is not None:
            if content_changed:
                stats.updated += 1  # still awaiting review: the queued item now holds the newer facts
            else:
                stats.unchanged += 1
        elif item.status != DiscoveredItemStatus.DUPLICATE:
            reasons = publishing.auto_publish_gates(self.settings, source=source, item=item, company=company_match.company)
            if not reasons:
                published_type, published = await publishing.materialize_item(self.db, item, publish=True, admin_id=None, company_id=item.company_id)
                stats.auto_published += 1
                await publishing.notify_company_followers(self.db, published_type, published)
            else:
                item.evidence_json = {**item.evidence_json, "auto_publish_blocked_by": reasons}

    async def _compare_with_record(self, source: ContentSource, item: DiscoveredItem, entity_type: str, entity, record, stats: RunStats) -> None:
        changes = diff_record(entity_type, entity, record)
        owned = getattr(entity, "content_source_id", None) == source.id
        if owned:
            entity.last_verified_at = _now()
            if getattr(entity, "source_state", None) == SourceState.SOURCE_REMOVED:
                # The listing is back at its source — resolve the pending removal instead of a new change.
                for change in await self._pending_changes(entity_type, entity.id, field="source_state"):
                    await publishing.dismiss_change(self.db, change, admin_id=None)
                entity.source_state = SourceState.ACTIVE
        recorded = 0
        for field_name, old, new in changes:
            change = await publishing.record_change(
                self.db, entity_type=entity_type, entity_id=entity.id, field=field_name, old=old, new=new, source_id=source.id, item_id=item.id,
            )
            if change is not None:
                recorded += 1
        if recorded:
            stats.changes_detected += recorded
            stats.updated += 1
            if item.status in (DiscoveredItemStatus.DUPLICATE, DiscoveredItemStatus.VERIFIED, DiscoveredItemStatus.NEW):
                item.status = DiscoveredItemStatus.NEEDS_REVIEW
            if owned and self.settings.auto_publish_discovery and source.auto_publish_allowed and source.verification_status == VerificationStatus.VERIFIED and not (item.evidence_json or {}).get("flags"):
                await self.db.flush()
                for change in await self._pending_changes(entity_type, entity.id):
                    await publishing.apply_change(self.db, change, admin_id=None)
        elif item.status in (DiscoveredItemStatus.NEW, DiscoveredItemStatus.VERIFIED, DiscoveredItemStatus.NEEDS_REVIEW) and item.created_draft_id is None:
            # Already in CareerOS with nothing new to review.
            item.status = DiscoveredItemStatus.DUPLICATE
            stats.duplicate += 1

    async def _pending_changes(self, entity_type: str, entity_id: str, field: str | None = None):
        from app.models.admin_ops import ChangeStatus, ContentChange

        query = select(ContentChange).where(ContentChange.entity_type == entity_type, ContentChange.entity_id == entity_id, ContentChange.status == ChangeStatus.PENDING)
        if field:
            query = query.where(ContentChange.field == field)
        return (await self.db.execute(query)).scalars().all()

    def _verify(self, source: ContentSource, listing: DiscoveredListing) -> tuple[ItemVerificationStatus, list[str], list[str]]:
        record = listing.record
        checks, flags = [], []
        source_domain = registrable_domain(source.url)
        listing_domain = registrable_domain(record.source_url)
        canonical = record_canonical_url(record)
        if source.source_type.value == "AGGREGATOR" or is_aggregator_url(record.source_url):
            flags.append("DISCOVERY_ONLY_SOURCE")
            return ItemVerificationStatus.UNVERIFIED, ["source is discovery-only; locate the official listing"], flags
        if is_aggregator_url(canonical):
            flags.append("APPLICATION_URL_ON_AGGREGATOR")
        on_official_host = listing_domain == source_domain or is_ats_url(record.source_url)
        if on_official_host:
            checks.append("listing URL is on the registered source's domain or its official ATS")
        else:
            flags.append("LISTING_OFF_SOURCE_DOMAIN")
        if listing.method == "AI_RESEARCH":
            if listing.evidence.get("flags"):
                return ItemVerificationStatus.MANUAL_REVIEW_REQUIRED, checks, flags
            checks.append("AI-extracted facts matched the fetched official page")
        elif listing.method in ("STRUCTURED_API", "STRUCTURED_DATA"):
            checks.append("fetched directly from structured data published by the source")
        else:
            checks.append("found in the source's feed")
        if flags:
            return ItemVerificationStatus.MANUAL_REVIEW_REQUIRED, checks, flags
        return ItemVerificationStatus.SOURCE_VERIFIED, checks, flags

    # ------------------------------------------------------------------------------------------
    async def _detect_removals(self, source: ContentSource, result: AdapterResult, stats: RunStats) -> None:
        seen = set(result.seen_ids) | {l.record.source_external_id for l in result.listings if l.record.source_external_id}
        seen_urls = {canonicalize_url(record_canonical_url(l.record)) for l in result.listings}
        active_items = (await self.db.execute(
            select(DiscoveredItem).where(DiscoveredItem.source_id == source.id, DiscoveredItem.status.in_(ACTIVE_ITEM_STATUSES))
        )).scalars().all()
        owned_jobs = (await self.db.execute(
            select(Job).where(Job.content_source_id == source.id, Job.status == ContentStatus.PUBLISHED, Job.source_state == SourceState.ACTIVE, Job.external_job_id.isnot(None))
        )).scalars().all()
        if not seen and len(active_items) + len(owned_jobs) >= EMPTY_RESULT_REMOVAL_GUARD:
            stats.warnings.append("source returned no listings; removal detection skipped this run")
            return

        handled_entities: set[str] = set()
        for item in active_items:
            key_present = (item.external_id in seen) if item.external_id else (item.canonical_url in seen_urls)
            if key_present:
                continue
            entity_type, entity = await publishing.linked_entity(self.db, item)
            if entity is not None:
                await self._mark_entity_removed(source, entity_type, entity, item)
                handled_entities.add(entity.id)
            item.status = DiscoveredItemStatus.SOURCE_REMOVED
            stats.removed += 1
        for job in owned_jobs:
            if job.id in handled_entities or job.external_job_id in seen:
                continue
            await self._mark_entity_removed(source, ENTITY_JOB, job, None)
            stats.removed += 1

    async def _mark_entity_removed(self, source: ContentSource, entity_type: str, entity, item: DiscoveredItem | None) -> None:
        if getattr(entity, "source_state", SourceState.ACTIVE) != SourceState.ACTIVE:
            return
        # Pending admin confirmation: hidden from active feeds, kept for history (spec §23, §67).
        await publishing.record_change(
            self.db, entity_type=entity_type, entity_id=entity.id, field="source_state",
            old=SourceState.ACTIVE.value, new=SourceState.SOURCE_REMOVED.value, source_id=source.id, item_id=item.id if item else None,
        )
        entity.source_state = SourceState.SOURCE_REMOVED
        audit_service.add(self.db, admin_id=None, action="source_removed", entity_type=entity_type.lower(), entity_id=entity.id, metadata={"source_id": source.id})

    # ------------------------------------------------------------------------------------------
    async def _finish(
        self,
        run: DiscoveryRun,
        source: ContentSource | None,
        status_value: DiscoveryRunStatus,
        started: float,
        stats: RunStats,
        *,
        error: tuple[str, str] | None = None,
        retry_after: float | None = None,
        touch_source: bool = True,
    ) -> DiscoveryRun:
        now = _now()
        run.status = status_value
        run.finished_at = now
        run.duration_ms = int((time.monotonic() - started) * 1000)
        run.items_found = stats.found
        run.items_new = stats.new
        run.items_updated = stats.updated
        run.items_duplicate = stats.duplicate
        run.items_invalid = stats.invalid
        run.items_removed = stats.removed
        if error:
            run.error_code, run.error_message = error[0], error[1][:500]

        if source is not None and touch_source:
            source.last_checked_at = now
            if status_value in (DiscoveryRunStatus.SUCCEEDED, DiscoveryRunStatus.PARTIAL):
                source.last_successful_fetch_at = now
                source.consecutive_failures = 0
                source.next_poll_after = None
                if source.verification_status == VerificationStatus.FAILING:
                    source.verification_status = VerificationStatus.UNVERIFIED
            else:
                source.last_error = (error[1] if error else status_value.value)[:500]
                source.last_error_at = now
                source.last_error_code = error[0] if error else status_value.value
                source.consecutive_failures = (source.consecutive_failures or 0) + 1
                if status_value == DiscoveryRunStatus.RATE_LIMITED:
                    wait = timedelta(seconds=retry_after) if retry_after else timedelta(minutes=source.crawl_interval_minutes)
                    source.next_poll_after = now + min(max(wait, timedelta(minutes=1)), MAX_RATE_LIMIT_BACKOFF)
                else:
                    source.next_poll_after = backoff_until(consecutive_failures=source.consecutive_failures, interval_minutes=source.crawl_interval_minutes, now=now)
                if source.consecutive_failures >= 3 and source.verification_status == VerificationStatus.UNVERIFIED:
                    source.verification_status = VerificationStatus.FAILING

        audit_service.add(
            self.db, admin_id=run.requested_by_admin_id, action="discovery_run", entity_type="discovery_run", entity_id=run.id,
            metadata={
                "source_id": run.source_id, "status": status_value.value, "found": stats.found, "new": stats.new,
                "updated": stats.updated, "duplicates": stats.duplicate, "removed": stats.removed, "error_code": run.error_code,
            },
        )
        await self.db.commit()
        logger.info(
            "discovery_run source_id=%s status=%s found=%s new=%s updated=%s duplicates=%s invalid=%s removed=%s ms=%s error=%s",
            run.source_id, status_value.value, stats.found, stats.new, stats.updated, stats.duplicate, stats.invalid, stats.removed, run.duration_ms, run.error_code,
        )
        return run
