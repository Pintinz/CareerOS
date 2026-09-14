"""Admin operational models: audit trail, runtime-configurable settings, the content source
registry + discovery queue + discovery runs + content change history (the live discovery engine —
see DISCOVERY_ENGINE.md), and a minimal notification-authoring model.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.job import SourceType, string_enum

__all__ = [
    "AdminNotification",
    "AuditLog",
    "ChangeStatus",
    "ContentChange",
    "ContentSource",
    "DiscoveredItem",
    "DiscoveredItemStatus",
    "DiscoveredItemType",
    "DiscoveryMethod",
    "DiscoveryRun",
    "DiscoveryRunStatus",
    "DiscoveryRunTrigger",
    "DiscoveryRunType",
    "ItemVerificationStatus",
    "NotificationAudience",
    "NotificationStatus",
    "ResearchCacheEntry",
    "SourceType",
    "SystemSetting",
    "VerificationStatus",
]


class AuditLog(Base):
    """Append-only — nothing in this codebase ever updates or deletes an AuditLog row. `metadata_json`
    must never contain a secret, token, or password (spec §34) — every call site in
    `app/services/audit_service.py` passes only small, non-sensitive identifiers/labels."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 255, not 36: most entity ids are UUIDs, but system settings are audited by key (e.g.
    # "email_classifier_confidence_thresholds", 38 chars). PostgreSQL enforces VARCHAR lengths, so
    # at 36 a settings change would commit and then fail its audit write (Phase 11 Postgres run).
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class SystemSetting(Base):
    """One row per runtime-configurable, non-secret value (spec §35) — a plain key/value(JSON)
    store, not a schema-per-setting table, so adding a new tunable never needs a migration.
    Secrets (API keys, OAuth client secrets) are never stored here — those stay in environment/
    secret management, per explicit spec instruction."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class VerificationStatus(str, enum.Enum):
    """Health of a registered source as a whole."""

    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"  # an admin confirmed the source belongs to the organization it claims.
    FAILING = "FAILING"


class DiscoveryMethod(str, enum.Enum):
    STRUCTURED_API = "STRUCTURED_API"  # public ATS job-board APIs (Lever, Greenhouse, ...)
    RSS = "RSS"
    STRUCTURED_DATA = "STRUCTURED_DATA"  # schema.org JSON-LD embedded in official pages
    AI_RESEARCH = "AI_RESEARCH"  # ResearchProvider interpretation of unstructured official pages
    MANUAL = "MANUAL"  # tracked for editors; never fetched automatically


class ContentSource(TimestampMixin, Base):
    """A registered place CareerOS pulls content from. Registration alone fetches nothing: a source
    is only polled when `is_active`, `polling_enabled`, the global WEB_DISCOVERY_ENABLED flag and
    its adapter's flag are all on (DISCOVERY_ENGINE.md)."""

    __tablename__ = "content_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)  # base URL
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    # 1 (discovery-only) … 5 (official organization source). Trust is not publish permission.
    trust_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    discovery_method: Mapped[DiscoveryMethod] = mapped_column(
        string_enum(DiscoveryMethod), nullable=False, default=DiscoveryMethod.MANUAL, server_default=DiscoveryMethod.MANUAL.value
    )
    # Which content types this source yields, e.g. ["JOB", "INTERNSHIP"]; used to classify items.
    content_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # Public, non-secret adapter parameters only (board token, company identifier, Workday site).
    adapter_config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    polling_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    crawl_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=720, server_default="720")
    auto_publish_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), nullable=False, default=VerificationStatus.UNVERIFIED
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Set after a 429/Retry-After or repeated failures: the dispatcher won't poll before this.
    next_poll_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class DiscoveredItemType(str, enum.Enum):
    JOB = "JOB"
    INTERNSHIP = "INTERNSHIP"
    GRADUATE_PROGRAM = "GRADUATE_PROGRAM"
    SCHOLARSHIP = "SCHOLARSHIP"
    FELLOWSHIP = "FELLOWSHIP"
    INTELLIGENCE = "INTELLIGENCE"


class DiscoveredItemStatus(str, enum.Enum):
    NEW = "NEW"  # just ingested, not yet evaluated
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"  # evidence checks passed; still awaits an editorial decision
    DUPLICATE = "DUPLICATE"
    IGNORED = "IGNORED"
    REJECTED = "REJECTED"
    DRAFT_CREATED = "DRAFT_CREATED"
    PUBLISHED = "PUBLISHED"
    SOURCE_REMOVED = "SOURCE_REMOVED"
    ERROR = "ERROR"


class ItemVerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"  # fetched from the registered official source/ATS itself
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"  # extracted facts not supported by the fetched page
    FETCH_FAILED = "FETCH_FAILED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class DiscoveryRunType(str, enum.Enum):
    SOURCE_DISCOVERY = "SOURCE_DISCOVERY"
    VERIFICATION = "VERIFICATION"


class DiscoveryRunTrigger(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class DiscoveryRunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"  # some items were invalid or a later page failed
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    SKIPPED = "SKIPPED"  # disabled by a feature flag / paused source


class DiscoveryRun(Base):
    """One execution of discovery for a source (or of active-listing re-verification). Created as
    QUEUED by the admin "Run Discovery" action or the dispatcher, then claimed by a worker."""

    __tablename__ = "discovery_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("content_sources.id", ondelete="CASCADE"), nullable=True, index=True
    )
    run_type: Mapped[DiscoveryRunType] = mapped_column(string_enum(DiscoveryRunType), nullable=False)
    trigger: Mapped[DiscoveryRunTrigger] = mapped_column(string_enum(DiscoveryRunTrigger), nullable=False)
    status: Mapped[DiscoveryRunStatus] = mapped_column(string_enum(DiscoveryRunStatus), nullable=False, index=True)
    requested_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_duplicate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_invalid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stats_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class DiscoveredItem(TimestampMixin, Base):
    """One candidate piece of content found via a `ContentSource`. Never published by default —
    the review flow (or, only when every auto-publish gate passes, the pipeline) is the only path
    to a real Job/Scholarship/IntelligencePost row. `raw_payload_json` is admin-only evidence and
    is never exposed through a public endpoint."""

    __tablename__ = "discovered_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("discovery_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_type: Mapped[DiscoveredItemType] = mapped_column(Enum(DiscoveredItemType), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    detected_title: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_url: Mapped[str] = mapped_column(String(1024), nullable=False)  # where it was found
    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Validated, normalized fields (app/ingestion/schemas.py) — what a draft is built from.
    extracted_data_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Why the item was accepted/flagged: source quality, matched organization, checks run.
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # A normalized (lowercased, whitespace-collapsed) title used for near-duplicate detection.
    normalized_title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    discovery_method: Mapped[DiscoveryMethod | None] = mapped_column(string_enum(DiscoveryMethod), nullable=True)
    verification_status: Mapped[ItemVerificationStatus] = mapped_column(
        string_enum(ItemVerificationStatus), nullable=False, default=ItemVerificationStatus.UNVERIFIED,
        server_default=ItemVerificationStatus.UNVERIFIED.value,
    )
    trust_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    duplicate_of_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("discovered_items.id", ondelete="SET NULL"), nullable=True
    )
    # The existing CareerOS record this item corresponds to (an update, not a new listing).
    matched_entity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    matched_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[DiscoveredItemStatus] = mapped_column(
        Enum(DiscoveredItemStatus), nullable=False, default=DiscoveredItemStatus.NEEDS_REVIEW, index=True
    )
    created_draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChangeStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    DISMISSED = "DISMISSED"


class ContentChange(TimestampMixin, Base):
    """Field-level change history for published content detected at its source (spec §20-21):
    e.g. JOB 1234 · application_deadline · 2026-09-30 → 2026-10-07 · detected 2026-09-14."""

    __tablename__ = "content_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # {"value": ...}
    new_value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True
    )
    discovered_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("discovered_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[ChangeStatus] = mapped_column(
        string_enum(ChangeStatus), nullable=False, default=ChangeStatus.PENDING, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class ResearchCacheEntry(Base):
    """Reuse of AI research results for unchanged pages (spec §75): keyed by provider + URL +
    content hash, so an unchanged page is never sent to a paid provider twice."""

    __tablename__ = "research_cache"
    __table_args__ = (UniqueConstraint("provider", "url", "content_hash", name="uq_research_cache_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationAudience(str, enum.Enum):
    ALL_USERS = "ALL_USERS"
    COMPANY_FOLLOWERS = "COMPANY_FOLLOWERS"
    JOB_MATCH = "JOB_MATCH"
    SCHOLARSHIP_INTERESTED = "SCHOLARSHIP_INTERESTED"
    SPECIFIC_USER = "SPECIFIC_USER"


class NotificationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    SENT = "SENT"
    CANCELLED = "CANCELLED"


class AdminNotification(TimestampMixin, Base):
    """An admin-authored push-notification campaign (spec §32-33). Recording one here does not by
    itself deliver a push notification — no FCM/APNs credentials are configured in this
    environment (see PROJECT_STATUS.md); `status` only ever reaches `SENT` via the (mock/no-op in
    dev) delivery step, which explicitly never touches audience members' private content."""

    __tablename__ = "admin_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    deep_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audience: Mapped[NotificationAudience] = mapped_column(Enum(NotificationAudience), nullable=False)
    audience_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # company/job/scholarship/user id.
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.DRAFT)
    recipient_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
