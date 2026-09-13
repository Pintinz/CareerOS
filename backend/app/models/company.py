from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    career_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 9 spec §9 — editorially entered, factual structured fields only. Never auto-populated
    # or inferred (no leadership/project data is fabricated anywhere in this codebase).
    known_technologies: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    business_areas: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    locations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
