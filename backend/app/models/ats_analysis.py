from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AtsAnalysis(TimestampMixin, Base):
    """One ATS Readiness / Job Match run (spec §15). Stores the full score breakdown so history
    (spec §47 "Analysis history") can show exactly how a past score was computed, not just the
    final number."""

    __tablename__ = "ats_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cv_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cv_documents.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    job_description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    strong_matches: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    formatting_issues: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_metrics_note: Mapped[str | None] = mapped_column(Text, nullable=True)
