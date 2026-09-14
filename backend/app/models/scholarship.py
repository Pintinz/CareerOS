import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.job import ContentStatus, SourceState, SourceType, string_enum


class DegreeLevel(str, enum.Enum):
    UNDERGRADUATE = "UNDERGRADUATE"
    MASTERS = "MASTERS"
    PHD = "PHD"
    OTHER = "OTHER"


class FundingType(str, enum.Enum):
    FULLY_FUNDED = "FULLY_FUNDED"
    PARTIAL = "PARTIAL"
    # Funding not stated by the source: never shown as "fully" or "partially" funded.
    UNSPECIFIED = "UNSPECIFIED"


class AwardType(str, enum.Enum):
    SCHOLARSHIP = "SCHOLARSHIP"
    FELLOWSHIP = "FELLOWSHIP"
    GRANT = "GRANT"


class Scholarship(TimestampMixin, Base):
    __tablename__ = "scholarships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Stored as JSON lists — a scholarship commonly targets multiple degree levels/fields.
    degree_levels: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    fields_of_study: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    funding_type: Mapped[FundingType] = mapped_column(Enum(FundingType), nullable=False, default=FundingType.PARTIAL)

    tuition_coverage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monthly_stipend: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_support: Mapped[str | None] = mapped_column(String(255), nullable=True)
    insurance_support: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accommodation_support: Mapped[str | None] = mapped_column(String(255), nullable=True)

    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    eligible_nationalities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    academic_requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    experience_requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    language_requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    age_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required_documents: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    post_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    official_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False, default=SourceType.OTHER)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    award_type: Mapped[AwardType] = mapped_column(
        string_enum(AwardType), nullable=False, default=AwardType.SCHOLARSHIP,
        server_default=AwardType.SCHOLARSHIP.value, index=True,
    )
    opening_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_state: Mapped[SourceState] = mapped_column(
        string_enum(SourceState), nullable=False, default=SourceState.ACTIVE,
        server_default=SourceState.ACTIVE.value, index=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ContentStatus] = mapped_column(Enum(ContentStatus), nullable=False, default=ContentStatus.DRAFT)
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


class SavedScholarship(TimestampMixin, Base):
    __tablename__ = "saved_scholarships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scholarship_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False, index=True
    )
