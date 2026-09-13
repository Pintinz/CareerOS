"""Phase 9 — admin operational models: audit trail, runtime-configurable settings, the content
source registry / discovery queue (architecture only — see ARCHITECTURE.md for what is and isn't
actually wired to a live ingestion adapter), and a minimal notification-authoring model.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


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
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
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


class SourceType(str, enum.Enum):
    OFFICIAL_CAREER_PAGE = "OFFICIAL_CAREER_PAGE"
    OFFICIAL_NEWSROOM = "OFFICIAL_NEWSROOM"
    INVESTOR_RELATIONS = "INVESTOR_RELATIONS"
    RSS = "RSS"
    LEVER = "LEVER"
    ASHBY = "ASHBY"
    UNIVERSITY = "UNIVERSITY"
    SCHOLARSHIP_PROVIDER = "SCHOLARSHIP_PROVIDER"
    GOVERNMENT = "GOVERNMENT"
    REGULATOR = "REGULATOR"
    INDUSTRY_PUBLICATION = "INDUSTRY_PUBLICATION"
    OTHER = "OTHER"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    FAILING = "FAILING"


class ContentSource(TimestampMixin, Base):
    """A registered place CareerOS could pull content from (spec §24). Registering a source here
    does **not** by itself ingest anything — see `app/ingestion/` and ARCHITECTURE.md's Discovery
    section for exactly which source types have a live adapter today (none do, in this
    environment) versus which are just tracked as metadata for a human editor to check manually."""

    __tablename__ = "content_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), nullable=False, default=VerificationStatus.UNVERIFIED
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class DiscoveredItemType(str, enum.Enum):
    JOB = "JOB"
    SCHOLARSHIP = "SCHOLARSHIP"
    INTELLIGENCE = "INTELLIGENCE"


class DiscoveredItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"  # a CareerOS draft was created from it.
    IGNORED = "IGNORED"
    REJECTED = "REJECTED"


class DiscoveredItem(TimestampMixin, Base):
    """One candidate piece of content found via a `ContentSource` (spec §25-27). Never
    auto-published — `POST /admin/discovery/{id}/create-draft` is the only path from here to a
    real Job/Scholarship/IntelligencePost row, and that row always starts at `ContentStatus.DRAFT`.
    """

    __tablename__ = "discovered_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[DiscoveredItemType] = mapped_column(Enum(DiscoveredItemType), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_title: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    raw_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # A normalized (lowercased, whitespace-collapsed) title used for near-duplicate detection
    # (spec §27) without needing a fuzzy-match library.
    normalized_title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status: Mapped[DiscoveredItemStatus] = mapped_column(
        Enum(DiscoveredItemStatus), nullable=False, default=DiscoveredItemStatus.PENDING
    )
    created_draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
