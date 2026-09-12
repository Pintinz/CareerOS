from datetime import datetime

from pydantic import BaseModel, Field

from app.models.question import QuestionDifficulty, QuestionType
from app.models.test_session import TestMode, TestStatus
from app.schemas.pagination import PaginatedResponse

# ---------------------------------------------------------------------------
# Categories / topics (consumer + admin read)
# ---------------------------------------------------------------------------


class QuestionCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None

    model_config = {"from_attributes": True}


class QuestionTopicOut(BaseModel):
    id: str
    category_id: str
    name: str
    slug: str
    field: str | None = None
    industry: str | None = None

    model_config = {"from_attributes": True}


class QuestionCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None


class QuestionTopicCreate(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=150)
    slug: str = Field(min_length=1, max_length=150)
    field: str | None = None
    industry: str | None = None


# ---------------------------------------------------------------------------
# Admin question bank CRUD
# ---------------------------------------------------------------------------


class QuestionOptionIn(BaseModel):
    option_text: str | None = None
    option_image_url: str | None = None
    is_correct: bool = False
    display_order: int = 0


class QuestionOptionAdminOut(QuestionOptionIn):
    id: str

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    question_type: QuestionType
    question_image_url: str | None = None
    passage_text: str | None = None
    category_id: str
    topic_id: str | None = None
    field: str | None = None
    industry: str | None = None
    job_role: str | None = None
    difficulty: QuestionDifficulty
    explanation: str | None = None
    marks: float = 1.0
    negative_marks: float = 0.0
    estimated_seconds: int = 60
    correct_numeric_value: float | None = None
    numeric_tolerance: float = 0.0
    is_active: bool = True
    is_demo: bool = False
    options: list[QuestionOptionIn] = []


class QuestionUpdate(BaseModel):
    question_text: str | None = None
    question_type: QuestionType | None = None
    question_image_url: str | None = None
    passage_text: str | None = None
    category_id: str | None = None
    topic_id: str | None = None
    field: str | None = None
    industry: str | None = None
    job_role: str | None = None
    difficulty: QuestionDifficulty | None = None
    explanation: str | None = None
    marks: float | None = None
    negative_marks: float | None = None
    estimated_seconds: int | None = None
    correct_numeric_value: float | None = None
    numeric_tolerance: float | None = None
    is_active: bool | None = None
    options: list[QuestionOptionIn] | None = None


class QuestionAdminOut(BaseModel):
    id: str
    question_text: str
    question_type: QuestionType
    question_image_url: str | None = None
    passage_text: str | None = None
    category_id: str
    topic_id: str | None = None
    field: str | None = None
    industry: str | None = None
    job_role: str | None = None
    difficulty: QuestionDifficulty
    explanation: str | None = None
    marks: float
    negative_marks: float
    estimated_seconds: int
    correct_numeric_value: float | None = None
    numeric_tolerance: float
    is_active: bool
    is_demo: bool
    options: list[QuestionOptionAdminOut] = []

    model_config = {"from_attributes": True}


class QuestionAdminListResponse(PaginatedResponse[QuestionAdminOut]):
    pass


# ---------------------------------------------------------------------------
# Test sessions (consumer)
# ---------------------------------------------------------------------------


class TestSessionCreate(BaseModel):
    mode: TestMode = TestMode.PRACTICE
    sections: list[str] = Field(default_factory=list, description="Category slugs; empty = mixed, all sections")
    difficulty: str = Field(default="MIXED", description="EASY|MEDIUM|HARD|EXPERT|MIXED")
    question_count: int = Field(default=20, ge=1, le=100)
    timing: str = Field(default="UNTIMED", description="UNTIMED|OVERALL")
    time_limit_minutes: int | None = None
    application_id: str | None = None
    job_id: str | None = None
    topic_slugs: list[str] | None = Field(
        default=None, description="Explicit topic slugs to bias generation toward (Practice Weak Areas)."
    )


class OptionOut(BaseModel):
    id: str
    option_text: str | None = None
    option_image_url: str | None = None
    display_order: int


class SessionAnswerStateOut(BaseModel):
    selected_option_ids: list[str] | None = None
    answer_numeric_value: float | None = None
    is_flagged: bool = False


class SessionQuestionOut(BaseModel):
    """Client-facing, active-exam shape — never includes which option is correct."""

    id: str  # the snapshot (test_session_questions) id — used in all subsequent answer calls
    order_index: int
    question_text: str
    question_type: QuestionType
    question_image_url: str | None = None
    passage_text: str | None = None
    difficulty: QuestionDifficulty
    marks: float
    negative_marks: float
    category_name: str
    topic_name: str | None = None
    topic_slug: str | None = None
    options: list[OptionOut] = []
    answer_state: SessionAnswerStateOut | None = None


class TestSessionOut(BaseModel):
    id: str
    mode: TestMode
    status: TestStatus
    application_id: str | None = None
    job_id: str | None = None
    config: dict
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    expires_at: datetime | None = None
    time_limit_seconds: int | None = None
    time_used_seconds: int | None = None
    auto_submitted: bool
    question_count: int
    total_marks: float
    score: float | None = None
    percentage: float | None = None
    correct_count: int | None = None
    incorrect_count: int | None = None
    unanswered_count: int | None = None
    section_breakdown: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TestSessionDetailOut(TestSessionOut):
    questions: list[SessionQuestionOut] = []
    server_time: datetime
    remaining_seconds: int | None = None


class TestSessionListResponse(PaginatedResponse[TestSessionOut]):
    pass


class AnswerUpdate(BaseModel):
    selected_option_ids: list[str] | None = None
    answer_numeric_value: float | None = None
    time_spent_seconds: int | None = None


class TestResultOut(BaseModel):
    session_id: str
    status: TestStatus
    score: float
    total_marks: float
    percentage: float
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    time_used_seconds: int | None = None
    time_limit_seconds: int | None = None
    auto_submitted: bool
    section_breakdown: dict
    performance_label: str


class ReviewOptionOut(OptionOut):
    is_correct: bool


class ReviewQuestionOut(BaseModel):
    id: str
    order_index: int
    question_text: str
    question_type: QuestionType
    question_image_url: str | None = None
    passage_text: str | None = None
    difficulty: QuestionDifficulty
    category_name: str
    topic_name: str | None = None
    topic_slug: str | None = None
    options: list[ReviewOptionOut] = []
    selected_option_ids: list[str] | None = None
    answer_numeric_value: float | None = None
    correct_numeric_value: float | None = None
    is_correct: bool | None = None
    marks_awarded: float | None = None
    explanation: str | None = None
    time_spent_seconds: int | None = None


class ReviewOut(BaseModel):
    session_id: str
    questions: list[ReviewQuestionOut]


class CategoryStat(BaseModel):
    attempted: int
    correct: int
    percentage: float


class TopicStat(BaseModel):
    category_name: str
    topic_slug: str | None = None
    attempted: int
    correct: int
    percentage: float


class AptitudeAnalyticsOut(BaseModel):
    tests_completed: int
    questions_answered: int
    average_score: float | None = None
    best_score: float | None = None
    average_time_per_question_seconds: float | None = None
    by_category: dict[str, CategoryStat]
    by_topic: dict[str, TopicStat]


class WeakTopicOut(BaseModel):
    topic_name: str
    topic_slug: str | None = None
    category_name: str
    accuracy: float
    attempted: int


class RecommendationsOut(BaseModel):
    weak_topics: list[WeakTopicOut]
    min_attempts_required: int
