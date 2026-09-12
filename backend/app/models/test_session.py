import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.question import QuestionDifficulty, QuestionType


class TestMode(str, enum.Enum):
    PRACTICE = "PRACTICE"
    TIMED = "TIMED"
    MOCK = "MOCK"
    JOB_SPECIFIC = "JOB_SPECIFIC"
    FIELD_SPECIFIC = "FIELD_SPECIFIC"
    COMPANY_SPECIFIC = "COMPANY_SPECIFIC"


class TestStatus(str, enum.Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"
    ABANDONED = "ABANDONED"


class TestSession(TimestampMixin, Base):
    """One assessment attempt. Timing is authoritative from `started_at`/`expires_at` timestamps,
    never from a client-reported "seconds remaining" — see ARCHITECTURE.md → Timer authority."""

    __tablename__ = "test_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    mode: Mapped[TestMode] = mapped_column(Enum(TestMode), nullable=False)
    status: Mapped[TestStatus] = mapped_column(Enum(TestStatus), nullable=False, default=TestStatus.CREATED)

    application_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )

    # What was requested at creation time (sections, difficulty mode, field/industry/job_role
    # context) — kept so "Retake" / "Practice Similar" can reproduce the same configuration.
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # NULL for untimed practice sessions — no expiry to enforce.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_used_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incorrect_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unanswered_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # {"<category_slug>": {"correct": n, "total": n, "percentage": p}, ...} — computed at grading
    # time, stored so results/review never need to re-join and re-aggregate historical sessions.
    section_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class TestSessionQuestion(TimestampMixin, Base):
    """A frozen snapshot of one question as shown in one session (spec §9). Editing the master
    `Question` row later must never change what a past session recorded — every field the user
    saw or that grading depends on is copied here at session-creation time."""

    __tablename__ = "test_session_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Kept only to support "Practice Similar Questions" (jump back to the live topic/category) —
    # never re-read for grading or display once the snapshot exists.
    question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True
    )

    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    question_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    passage_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(Enum(QuestionDifficulty), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    negative_marks: Mapped[float] = mapped_column(Float, nullable=False)

    category_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    topic_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Kept alongside topic_name so weak-topic analytics can feed a topic slug straight back into
    # a new session's `topic_slugs` override (the "Practice Weak Areas" flow) without a fragile
    # name-based lookup.
    topic_slug: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # [{"id": ..., "option_text": ..., "option_image_url": ..., "display_order": ...}, ...] —
    # deliberately WITHOUT is_correct. Never sent to the client until the session is submitted.
    options_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Kept server-side only — grading reference. [option_id, ...] for choice questions.
    correct_option_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    correct_numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    numeric_tolerance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class TestAnswer(TimestampMixin, Base):
    __tablename__ = "test_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_session_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    selected_option_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    answer_numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Graded at submit time — null until then, so "has this been answered/graded" is unambiguous.
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    marks_awarded: Mapped[float | None] = mapped_column(Float, nullable=True)
