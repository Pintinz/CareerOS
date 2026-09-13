from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class MediaAsset(TimestampMixin, Base):
    """Audit/metadata record for every image uploaded through the shared admin upload pipeline
    (`POST /admin/uploads/image`) — reused by jobs/companies/scholarships (existing) and now
    aptitude/interview question authoring (Phase 7.5 spec §12-13), rather than a separate
    per-feature upload implementation. The binary itself lives on local disk (or, later, a real
    object-storage provider behind the same `StorageProvider` interface) — never duplicated into
    Postgres."""

    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
