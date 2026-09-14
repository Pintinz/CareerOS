import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.job import ContentStatus, SourceType


class IntelligenceCategory(str, enum.Enum):
    LEADERSHIP = "LEADERSHIP"
    TECHNOLOGY = "TECHNOLOGY"
    AUTOMATION = "AUTOMATION"
    INVESTMENTS = "INVESTMENTS"
    HIRING = "HIRING"
    PROJECTS = "PROJECTS"
    ACQUISITION = "ACQUISITION"
    PLANT_EXPANSION = "PLANT_EXPANSION"
    MANUFACTURING = "MANUFACTURING"
    ENERGY = "ENERGY"
    FINANCE = "FINANCE"
    AI = "AI"
    GRADUATE_RECRUITMENT = "GRADUATE_RECRUITMENT"
    OPERATIONS = "OPERATIONS"
    OTHER = "OTHER"


class IntelligencePost(TimestampMixin, Base):
    """Company intelligence / news feed item (spec §19-20). `why_it_matters` is admin-written,
    not generated — the app has no AI summarizer, and spec §20 requires hedged language
    ('may increase relevance of...') that a human editor commits to, not an algorithm."""

    __tablename__ = "intelligence_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )

    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[IntelligenceCategory] = mapped_column(Enum(IntelligenceCategory), nullable=False)

    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    post_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    full_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevant_roles: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    relevant_skills: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False, default=SourceType.OTHER)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True, index=True
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
