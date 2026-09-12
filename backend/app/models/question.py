import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class QuestionType(str, enum.Enum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TRUE_FALSE = "TRUE_FALSE"
    NUMERIC = "NUMERIC"
    IMAGE_BASED = "IMAGE_BASED"
    PASSAGE_BASED = "PASSAGE_BASED"


class QuestionDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"


class QuestionCategory(TimestampMixin, Base):
    """The six fixed top-level sections from spec §4/§27 (Numerical/Verbal/Abstract/Logical/
    Situational/Technical). Modeled as real admin-manageable rows, not a hardcoded enum, even
    though the master spec only ever names these six — Phase 9's admin UI can rename/describe
    them without a schema change."""

    __tablename__ = "question_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class QuestionTopic(TimestampMixin, Base):
    """A topic within a category (e.g. "Percentages" under Numerical, "Pumps" under Technical —
    spec §12/§15). `field`/`industry` let a Technical topic be scoped (e.g. "Pumps" is Mechanical/
    Oil & Gas) so the job-specific generation engine can match on them (spec §11/§15)."""

    __tablename__ = "question_topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    field: Mapped[str | None] = mapped_column(String(150), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(150), nullable=True)


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    question_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Only meaningful for PASSAGE_BASED — multiple questions can share the same passage text by
    # simply repeating it verbatim; no separate passages table (documented simplification).
    passage_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("question_topics.id", ondelete="SET NULL"), nullable=True, index=True
    )

    field: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    job_role: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)

    difficulty: Mapped[QuestionDifficulty] = mapped_column(Enum(QuestionDifficulty), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    marks: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    negative_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    # Only used when question_type == NUMERIC — the option-based tables below don't apply.
    correct_numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    numeric_tolerance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class QuestionOption(TimestampMixin, Base):
    __tablename__ = "question_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
