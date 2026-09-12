from datetime import datetime

from pydantic import BaseModel, Field

from app.models.interview import InterviewDifficulty, InterviewSessionMode, InterviewSessionStatus, StarCategory
from app.models.job import ExperienceLevel
from app.schemas.pagination import PaginatedResponse

# ---------------------------------------------------------------------------
# Categories / topics
# ---------------------------------------------------------------------------


class InterviewCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None

    model_config = {"from_attributes": True}


class InterviewTopicOut(BaseModel):
    id: str
    category_id: str
    name: str
    slug: str
    field: str | None = None
    industry: str | None = None

    model_config = {"from_attributes": True}


class InterviewCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None


class InterviewTopicCreate(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=150)
    slug: str = Field(min_length=1, max_length=150)
    field: str | None = None
    industry: str | None = None


# ---------------------------------------------------------------------------
# Admin question CRUD
# ---------------------------------------------------------------------------


class AnswerGuidance(BaseModel):
    assessing: str | None = None
    strong_answer_includes: list[str] = []
    common_mistakes: list[str] = []
    technical_concepts: list[str] = []


class InterviewQuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    category_id: str
    topic_id: str | None = None
    field: str | None = None
    industry: str | None = None
    job_role: str | None = None
    company_id: str | None = None
    experience_level: ExperienceLevel | None = None
    difficulty: InterviewDifficulty
    answer_guidance: AnswerGuidance | None = None
    evaluation_points: list[str] = []
    follow_up_prompt: str | None = None
    star_tags: list[str] = []
    is_active: bool = True
    is_demo: bool = False


class InterviewQuestionUpdate(BaseModel):
    question_text: str | None = None
    category_id: str | None = None
    topic_id: str | None = None
    field: str | None = None
    industry: str | None = None
    job_role: str | None = None
    company_id: str | None = None
    experience_level: ExperienceLevel | None = None
    difficulty: InterviewDifficulty | None = None
    answer_guidance: AnswerGuidance | None = None
    evaluation_points: list[str] | None = None
    follow_up_prompt: str | None = None
    star_tags: list[str] | None = None
    is_active: bool | None = None


class InterviewQuestionAdminOut(BaseModel):
    id: str
    question_text: str
    category_id: str
    topic_id: str | None = None
    field: str | None = None
    industry: str | None = None
    job_role: str | None = None
    company_id: str | None = None
    experience_level: ExperienceLevel | None = None
    difficulty: InterviewDifficulty
    answer_guidance: dict | None = None
    evaluation_points: list | None = None
    follow_up_prompt: str | None = None
    star_tags: list | None = None
    is_active: bool
    is_demo: bool

    model_config = {"from_attributes": True}


class InterviewQuestionAdminListResponse(PaginatedResponse[InterviewQuestionAdminOut]):
    pass


# ---------------------------------------------------------------------------
# Sessions (consumer)
# ---------------------------------------------------------------------------


class InterviewSessionCreate(BaseModel):
    mode: InterviewSessionMode = InterviewSessionMode.PRACTICE
    categories: list[str] = Field(default_factory=list, description="Category slugs; empty = mixed, all categories")
    category_counts: dict[str, int] | None = Field(
        default=None, description="Category slug -> exact question count (Mock Interview builder)"
    )
    difficulty: str = Field(default="MIXED", description="EASY|MEDIUM|HARD|EXPERT|MIXED")
    question_count: int = Field(default=10, ge=1, le=50)
    time_per_question_seconds: int | None = None
    application_id: str | None = None
    job_id: str | None = None
    company_id: str | None = None
    experience_level: ExperienceLevel | None = Field(
        default=None, description="When ENTRY/JUNIOR, EXPERT-difficulty questions are excluded from a MIXED session unless explicitly requested."
    )


class AnswerStructureCheckOut(BaseModel):
    word_count: int
    has_metric: bool
    star_hints: dict[str, bool]
    flags: list[str]


class SessionAnswerStateOut(BaseModel):
    answer_text: str | None = None
    notes: str | None = None
    audio_path: str | None = None
    audio_duration_seconds: int | None = None
    self_rating: int | None = None
    used_star: bool | None = None
    gave_measurable_result: bool | None = None
    answered_exact_question: bool | None = None
    is_skipped: bool = False
    is_marked_practiced: bool = False
    is_saved: bool = False
    structure_check: AnswerStructureCheckOut | None = None


class SessionQuestionOut(BaseModel):
    id: str
    order_index: int
    question_text: str
    category_name: str
    topic_name: str | None = None
    difficulty: InterviewDifficulty
    answer_guidance: dict | None = None
    evaluation_points: list | None = None
    follow_up_prompt: str | None = None
    suggested_star_story_ids: list[str] = []
    time_limit_seconds: int | None = None
    answer_state: SessionAnswerStateOut | None = None


class InterviewSessionOut(BaseModel):
    id: str
    mode: InterviewSessionMode
    status: InterviewSessionStatus
    application_id: str | None = None
    job_id: str | None = None
    company_id: str | None = None
    categories_requested: list
    question_count: int
    time_per_question_seconds: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewSessionDetailOut(InterviewSessionOut):
    questions: list[SessionQuestionOut] = []


class InterviewSessionListResponse(PaginatedResponse[InterviewSessionOut]):
    pass


class AnswerUpdate(BaseModel):
    answer_text: str | None = None
    notes: str | None = None
    audio_path: str | None = None
    audio_duration_seconds: int | None = None
    self_rating: int | None = Field(default=None, ge=1, le=5)
    used_star: bool | None = None
    gave_measurable_result: bool | None = None
    answered_exact_question: bool | None = None
    is_skipped: bool | None = None
    is_marked_practiced: bool | None = None
    is_saved: bool | None = None


class CategoryCompletionOut(BaseModel):
    completed: int
    total: int


class SessionCompletionOut(BaseModel):
    session_id: str
    questions_completed: int
    questions_skipped: int
    average_self_rating: float | None = None
    average_answer_length: float | None = None
    star_usage_rate: float | None = None
    category_breakdown: dict[str, CategoryCompletionOut]
    areas_practiced: list[str]
    areas_still_uncovered: list[str]


# ---------------------------------------------------------------------------
# STAR stories
# ---------------------------------------------------------------------------


class StarStoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: StarCategory
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    lessons: str | None = None
    skills_demonstrated: list[str] = []
    metrics: str | None = None
    company_context: str | None = None
    relevant_roles: list[str] = []
    relevant_questions: list[str] = []


class StarStoryUpdate(BaseModel):
    title: str | None = None
    category: StarCategory | None = None
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    lessons: str | None = None
    skills_demonstrated: list[str] | None = None
    metrics: str | None = None
    company_context: str | None = None
    relevant_roles: list[str] | None = None
    relevant_questions: list[str] | None = None


class StarCompletenessOut(BaseModel):
    sections: dict[str, str]
    gaps: list[str]
    is_complete: bool


class StarStoryOut(BaseModel):
    id: str
    title: str
    category: StarCategory
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    lessons: str | None = None
    skills_demonstrated: list | None = None
    metrics: str | None = None
    company_context: str | None = None
    relevant_roles: list | None = None
    relevant_questions: list | None = None
    completeness: StarCompletenessOut
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Analytics / readiness
# ---------------------------------------------------------------------------


class InterviewAnalyticsOut(BaseModel):
    sessions_completed: int
    questions_practiced: int
    average_self_rating: float | None = None
    star_stories_created: int
    star_stories_ready: int
    company_prep_completed: int
    technical_topics_covered: int
    by_category: dict[str, CategoryCompletionOut]


class ReadinessComponentsOut(BaseModel):
    question_practice: float | None = None
    star_coverage: float | None = None
    company_prep: float | None = None
    job_specific_prep: float | None = None
    technical_prep: float | None = None
    recent_consistency: float | None = None


class ReadinessOut(BaseModel):
    overall: float | None = None
    insufficient_data: bool
    components: ReadinessComponentsOut


# ---------------------------------------------------------------------------
# Company / job preparation, checklist, questions to ask
# ---------------------------------------------------------------------------


class RecentDevelopmentOut(BaseModel):
    id: str
    headline: str
    summary: str | None = None
    published_at: datetime | None = None


class OpenJobOut(BaseModel):
    id: str
    title: str
    location: str | None = None


class CompanyPrepOut(BaseModel):
    company_id: str | None = None
    company_name: str | None = None
    industry: str | None = None
    about: str | None = None
    recent_developments: list[RecentDevelopmentOut] = []
    role_relevance: str | None = None
    likely_topics: list[str] = []
    open_jobs: list[OpenJobOut] = []
    disclaimer: str = (
        "CareerOS practice based on the company, role and available public information. "
        "Not an official employer interview guide."
    )


class ChecklistItemOut(BaseModel):
    key: str
    label: str
    is_done: bool


class QuestionToAskOut(BaseModel):
    id: str
    text: str
    category: str
    status: str | None = None  # "saved" | "planned" | None
    is_custom: bool = False


class PreparationProgressOut(BaseModel):
    application_id: str | None = None
    checklist: list[ChecklistItemOut]
    questions_to_ask: list[QuestionToAskOut]
    reviewed_topics: list[str]


class ChecklistUpdate(BaseModel):
    key: str
    is_done: bool


class QuestionToAskUpdate(BaseModel):
    id: str | None = None
    text: str | None = None
    category: str | None = None
    status: str | None = None
    is_custom: bool = False


class TopicReviewUpdate(BaseModel):
    topic_slug: str
    is_reviewed: bool
