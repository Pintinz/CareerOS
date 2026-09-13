import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ApplicationStage(str, enum.Enum):
    """Spec §36. Not every application uses every stage — the mobile timeline only shows
    stages that have actually happened plus the next expected one, not this whole list."""

    SAVED = "SAVED"
    APPLIED = "APPLIED"
    APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    APTITUDE_TEST = "APTITUDE_TEST"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    RECRUITER_SCREEN = "RECRUITER_SCREEN"
    INTERVIEW = "INTERVIEW"
    FINAL_INTERVIEW = "FINAL_INTERVIEW"
    ASSESSMENT_CENTRE = "ASSESSMENT_CENTRE"
    BACKGROUND_CHECK = "BACKGROUND_CHECK"
    MEDICAL = "MEDICAL"
    OFFER = "OFFER"
    HIRED = "HIRED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"
    NO_RESPONSE = "NO_RESPONSE"


# Stages that mean the application is no longer actively progressing — used to decide whether
# an application counts as "active" (spec §11 Home dashboard "Active Applications" card).
TERMINAL_STAGES = {
    ApplicationStage.HIRED,
    ApplicationStage.REJECTED,
    ApplicationStage.WITHDRAWN,
    ApplicationStage.EXPIRED,
}


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # A tracked application can reference a real job in our system, or be entered manually for
    # a role that isn't (spec §36-37) — job_id is optional and survives job deletion.
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    cv_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cv_documents.id", ondelete="SET NULL"), nullable=True
    )

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    current_stage: Mapped[ApplicationStage] = mapped_column(
        Enum(ApplicationStage), nullable=False, default=ApplicationStage.SAVED, index=True
    )
    applied_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interview_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assessment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    salary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ApplicationStageEvent(TimestampMixin, Base):
    """One entry in an application's timeline. Created automatically whenever `current_stage`
    changes — never edited after the fact, so the timeline is an honest history."""

    __tablename__ = "application_stage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[ApplicationStage] = mapped_column(Enum(ApplicationStage), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Distinguishes a manual "I updated this myself" event from one confirmed via the (future)
    # email-detection flow, spec §42 — always MANUAL until Phase 8 exists.
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")


class ApplicationNote(TimestampMixin, Base):
    __tablename__ = "application_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
