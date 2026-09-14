import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class EmploymentType(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    TEMPORARY = "TEMPORARY"
    VOLUNTEER = "VOLUNTEER"
    # A discovered listing that doesn't state its employment type is never labelled full-time.
    UNSPECIFIED = "UNSPECIFIED"


class WorkMode(str, enum.Enum):
    ON_SITE = "ON_SITE"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    # Discovery never guesses a work mode the source doesn't state (DISCOVERY_ENGINE.md).
    UNSPECIFIED = "UNSPECIFIED"


class ExperienceLevel(str, enum.Enum):
    ENTRY = "ENTRY"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD = "LEAD"
    EXECUTIVE = "EXECUTIVE"


class SourceType(str, enum.Enum):
    """The one source-type vocabulary shared by content rows and the source registry. It used to
    be two Python enums with different value lists mapped to the same PostgreSQL type name
    (`sourcetype`), so registry-only values could not be stored on PostgreSQL."""

    # Tier 1 — authoritative
    OFFICIAL_CAREER_PAGE = "OFFICIAL_CAREER_PAGE"
    OFFICIAL_NEWSROOM = "OFFICIAL_NEWSROOM"
    INVESTOR_RELATIONS = "INVESTOR_RELATIONS"
    GOVERNMENT = "GOVERNMENT"
    REGULATOR = "REGULATOR"
    UNIVERSITY = "UNIVERSITY"
    SCHOLARSHIP_PROVIDER = "SCHOLARSHIP_PROVIDER"
    # Tier 2 — official public ATS infrastructure
    GREENHOUSE = "GREENHOUSE"
    LEVER = "LEVER"
    ASHBY = "ASHBY"
    SMARTRECRUITERS = "SMARTRECRUITERS"
    WORKDAY = "WORKDAY"
    SUCCESSFACTORS = "SUCCESSFACTORS"
    ORACLE = "ORACLE"
    # Tier 3 — reputable discovery sources
    RSS = "RSS"
    INDUSTRY_PUBLICATION = "INDUSTRY_PUBLICATION"
    NEWS_MEDIA = "NEWS_MEDIA"
    # Tier 4 — discovery only, never canonical
    AGGREGATOR = "AGGREGATOR"
    OTHER = "OTHER"


class OpportunityType(str, enum.Enum):
    JOB = "JOB"
    INTERNSHIP = "INTERNSHIP"
    GRADUATE_PROGRAM = "GRADUATE_PROGRAM"


class SourceState(str, enum.Enum):
    """What CareerOS last established about the listing at its source (spec §22). Independent of
    the editorial `ContentStatus`: a PUBLISHED job whose source disappeared is SOURCE_REMOVED
    until an admin confirms, and is kept (never deleted) for users who saved or tracked it."""

    ACTIVE = "ACTIVE"
    DEADLINE_PASSED = "DEADLINE_PASSED"
    CLOSED = "CLOSED"
    SOURCE_REMOVED = "SOURCE_REMOVED"
    EXPIRED = "EXPIRED"
    UNKNOWN_REQUIRES_REVIEW = "UNKNOWN_REQUIRES_REVIEW"


def string_enum(enum_cls: type[enum.Enum]) -> Enum:
    """New enum columns are stored as plain VARCHAR (no native PostgreSQL ENUM type), so adding a
    value later never needs an `ALTER TYPE` migration. Validation stays in the Python enum."""
    return Enum(enum_cls, native_enum=False, create_constraint=False, length=40)


class ContentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # RESTRICT, not CASCADE (Phase 9.5 audit finding): Jobs are the primary public content type and
    # a Company with live/historical Jobs (and the Applications/TestSessions/AtsAnalyses that
    # reference them) should never be silently wiped out by deleting its Company row. An admin must
    # archive/reassign a company's jobs first — the database now enforces that instead of only
    # documenting it.
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    employment_type: Mapped[EmploymentType] = mapped_column(Enum(EmploymentType), nullable=False)
    work_mode: Mapped[WorkMode] = mapped_column(Enum(WorkMode), nullable=False)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(Enum(ExperienceLevel), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Whole-currency-unit integers (not minor units) — salary ranges don't need cent precision
    # and admin-side editing is simpler as plain numbers; see DATABASE.md for the rationale.
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    salary_period: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "yearly", "monthly"

    short_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_skills: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    benefits: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    post_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    application_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    application_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    application_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False, default=SourceType.OTHER)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Live discovery (DISCOVERY_ENGINE.md). All nullable/defaulted: manually authored jobs keep
    # working exactly as before.
    opportunity_type: Mapped[OpportunityType] = mapped_column(
        string_enum(OpportunityType), nullable=False, default=OpportunityType.JOB,
        server_default=OpportunityType.JOB.value, index=True,
    )
    external_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    requisition_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    state_or_region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    experience_requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # Graduate programme / internship specifics — only what the source explicitly states.
    program_duration: Mapped[str | None] = mapped_column(String(255), nullable=True)
    program_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eligibility_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_state: Mapped[SourceState] = mapped_column(
        string_enum(SourceState), nullable=False, default=SourceState.ACTIVE,
        server_default=SourceState.ACTIVE.value, index=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), nullable=False, default=ContentStatus.DRAFT, index=True
    )
    # Phase 9 editorial workflow (spec §13/§14) — set only when a background job or an explicit
    # publish action actually transitions status to PUBLISHED at/after this time, never before.
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    published_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class SavedJob(TimestampMixin, Base):
    __tablename__ = "saved_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
