import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.job import ExperienceLevel


class InterviewDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"


class InterviewSessionMode(str, enum.Enum):
    PRACTICE = "PRACTICE"
    MOCK = "MOCK"


class InterviewSessionStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class StarCategory(str, enum.Enum):
    SAFETY = "SAFETY"
    LEADERSHIP = "LEADERSHIP"
    TEAMWORK = "TEAMWORK"
    CONFLICT = "CONFLICT"
    EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    PROCESS_IMPROVEMENT = "PROCESS_IMPROVEMENT"
    FAILURE_LESSON = "FAILURE_LESSON"
    PRESSURE = "PRESSURE"
    ACHIEVEMENT = "ACHIEVEMENT"
    CUSTOMER = "CUSTOMER"
    INNOVATION = "INNOVATION"
    COMMUNICATION = "COMMUNICATION"
    DECISION_MAKING = "DECISION_MAKING"


class InterviewQuestionCategory(TimestampMixin, Base):
    """The ten fixed interview categories (spec §6) — modeled as real admin-manageable rows,
    same convention as aptitude's `question_categories`."""

    __tablename__ = "interview_question_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class InterviewTopic(TimestampMixin, Base):
    """A topic within a category — e.g. "Pumps" under Technical. `field`/`industry` scope it for
    the job-specific generation engine, same pattern as aptitude's `question_topics`."""

    __tablename__ = "interview_topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_question_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    field: Mapped[str | None] = mapped_column(String(150), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(150), nullable=True)


class InterviewQuestion(TimestampMixin, Base):
    __tablename__ = "interview_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_question_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("interview_topics.id", ondelete="SET NULL"), nullable=True, index=True
    )

    field: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    job_role: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    # Editorial tagging only ("recommended practice for this company/role") — never evidence that
    # this is a real leaked interview question from that employer. See PRIVACY.md / spec §35.
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )

    experience_level: Mapped[ExperienceLevel | None] = mapped_column(Enum(ExperienceLevel), nullable=True)
    difficulty: Mapped[InterviewDifficulty] = mapped_column(Enum(InterviewDifficulty), nullable=False)

    # Structured, deterministic guidance — never presented as AI-generated or employer-official.
    # Shape: {"assessing": str, "strong_answer_includes": [str], "common_mistakes": [str],
    #          "technical_concepts": [str]}
    answer_guidance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluation_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    follow_up_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # STAR category slugs this question is a good match for (spec §16 STAR suggestion) — e.g. a
    # "tell me about a difficult problem" question tags ["problem-solving", "equipment-failure"].
    star_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class InterviewSession(TimestampMixin, Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    mode: Mapped[InterviewSessionMode] = mapped_column(Enum(InterviewSessionMode), nullable=False)
    status: Mapped[InterviewSessionStatus] = mapped_column(
        Enum(InterviewSessionStatus), nullable=False, default=InterviewSessionStatus.IN_PROGRESS
    )

    application_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )

    # What was requested at creation time — lets a session be reproduced/retaken identically.
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    categories_requested: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Per-question time budget shown to the user during a Mock Interview — informational/self-paced
    # only; unlike the aptitude engine's server-enforced overall timer, nothing here forces
    # submission when it elapses (documented limitation, see ARCHITECTURE.md).
    time_per_question_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class InterviewSessionQuestion(TimestampMixin, Base):
    """A frozen snapshot of one interview question as shown in one session — same rationale as
    aptitude's `test_session_questions`: editing the master question bank later must never change
    what a past session recorded."""

    __tablename__ = "interview_session_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )

    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    topic_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    difficulty: Mapped[InterviewDifficulty] = mapped_column(Enum(InterviewDifficulty), nullable=False)
    answer_guidance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluation_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    follow_up_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    star_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class InterviewAnswer(TimestampMixin, Base):
    __tablename__ = "interview_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_session_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Local-file reference only — the binary audio is never uploaded to this backend (spec §19/§37).
    audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audio_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Transparent self-assessment (spec §21) — explicitly user-rated, never system-inferred.
    self_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_star: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gave_measurable_result: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    answered_exact_question: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    is_skipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_marked_practiced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Computed deterministically from answer_text at save time — see app/interview/answer_check.py.
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StarStory(TimestampMixin, Base):
    __tablename__ = "star_stories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[StarCategory] = mapped_column(Enum(StarCategory), nullable=False)

    situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    task: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    lessons: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_demonstrated: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_context: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relevant_roles: Mapped[list | None] = mapped_column(JSON, nullable=True)
    relevant_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)


class InterviewPreparationProgress(TimestampMixin, Base):
    """Per-user (optionally per-application) preparation state: the company-research checklist
    and the "questions to ask the interviewer" the user has saved/planned. `application_id=None`
    is the general (not application-linked) progress row."""

    __tablename__ = "interview_preparation_progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # {"understand_business": bool, "review_developments": bool, ...} — see app/interview/checklist.py
    checklist: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # [{"id": str, "text": str, "category": str, "status": "saved"|"planned", "is_custom": bool}]
    questions_to_ask: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Technical topic slugs (reusing the aptitude taxonomy's slugs) the user has marked reviewed.
    reviewed_topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
