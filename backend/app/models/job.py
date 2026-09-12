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


class WorkMode(str, enum.Enum):
    ON_SITE = "ON_SITE"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"


class ExperienceLevel(str, enum.Enum):
    ENTRY = "ENTRY"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD = "LEAD"
    EXECUTIVE = "EXECUTIVE"


class SourceType(str, enum.Enum):
    OFFICIAL_CAREER_PAGE = "OFFICIAL_CAREER_PAGE"
    OFFICIAL_NEWSROOM = "OFFICIAL_NEWSROOM"
    RSS = "RSS"
    LEVER = "LEVER"
    ASHBY = "ASHBY"
    OTHER = "OTHER"


class ContentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
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

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[ContentStatus] = mapped_column(Enum(ContentStatus), nullable=False, default=ContentStatus.DRAFT)

    created_by_admin_id: Mapped[str | None] = mapped_column(
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
