from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.interview import InterviewSessionStatus
from app.models.user import User
from app.repositories.interview_repository import InterviewCategoryRepository, InterviewTopicRepository
from app.schemas.interview import (
    AnswerUpdate,
    ChecklistUpdate,
    CompanyPrepOut,
    InterviewAnalyticsOut,
    InterviewCategoryOut,
    InterviewSessionCreate,
    InterviewSessionDetailOut,
    InterviewSessionListResponse,
    InterviewTopicOut,
    PreparationProgressOut,
    QuestionToAskUpdate,
    ReadinessOut,
    SessionCompletionOut,
    SessionQuestionOut,
    StarStoryCreate,
    StarStoryOut,
    StarStoryUpdate,
    TopicReviewUpdate,
)
from app.security.dependencies import get_current_user
from app.services.interview_service import InterviewService

router = APIRouter()


@router.get("/categories", response_model=list[InterviewCategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[InterviewCategoryOut]:
    categories = await InterviewCategoryRepository(db).list_all()
    return [InterviewCategoryOut.model_validate(c) for c in categories]


@router.get("/topics", response_model=list[InterviewTopicOut])
async def list_topics(category_id: str | None = None, db: AsyncSession = Depends(get_db)) -> list[InterviewTopicOut]:
    topics = await InterviewTopicRepository(db).list_all(category_id=category_id)
    return [InterviewTopicOut.model_validate(t) for t in topics]


@router.post("/sessions", response_model=InterviewSessionDetailOut, status_code=201)
async def create_session(
    payload: InterviewSessionCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> InterviewSessionDetailOut:
    return await InterviewService(db).create_session(user.id, payload)


@router.get("/sessions", response_model=InterviewSessionListResponse)
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: InterviewSessionStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewSessionListResponse:
    items, total = await InterviewService(db).list_for_user(
        user.id, page=page, page_size=page_size, status_filter=status_filter.value if status_filter else None
    )
    return InterviewSessionListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/sessions/{session_id}", response_model=InterviewSessionDetailOut)
async def get_session(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> InterviewSessionDetailOut:
    return await InterviewService(db).get_session_detail(user.id, session_id)


@router.put("/sessions/{session_id}/answers/{question_id}", response_model=SessionQuestionOut)
async def update_answer(
    session_id: str,
    question_id: str,
    payload: AnswerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionQuestionOut:
    return await InterviewService(db).update_answer(user.id, session_id, question_id, payload)


@router.post("/sessions/{session_id}/complete", response_model=SessionCompletionOut)
async def complete_session(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SessionCompletionOut:
    return await InterviewService(db).complete_session(user.id, session_id)


@router.get("/analytics", response_model=InterviewAnalyticsOut)
async def get_analytics(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> InterviewAnalyticsOut:
    return await InterviewService(db).get_analytics(user.id)


@router.get("/readiness", response_model=ReadinessOut)
async def get_readiness(
    application_id: str | None = None, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ReadinessOut:
    return await InterviewService(db).get_readiness(user.id, application_id)


@router.get("/prep/company", response_model=CompanyPrepOut)
async def get_company_prep(
    application_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CompanyPrepOut:
    return await InterviewService(db).get_company_prep(user.id, application_id)


@router.get("/prep/progress", response_model=PreparationProgressOut)
async def get_preparation_progress(
    application_id: str | None = None, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> PreparationProgressOut:
    return await InterviewService(db).get_preparation_progress(user.id, application_id)


@router.put("/prep/checklist", response_model=PreparationProgressOut)
async def update_checklist(
    payload: ChecklistUpdate,
    application_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PreparationProgressOut:
    return await InterviewService(db).update_checklist_item(user.id, application_id, payload.key, payload.is_done)


@router.put("/prep/questions-to-ask", response_model=PreparationProgressOut)
async def update_question_to_ask(
    payload: QuestionToAskUpdate,
    application_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PreparationProgressOut:
    return await InterviewService(db).update_question_to_ask(user.id, application_id, payload)


@router.put("/prep/topics", response_model=PreparationProgressOut)
async def update_topic_review(
    payload: TopicReviewUpdate,
    application_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PreparationProgressOut:
    return await InterviewService(db).update_topic_review(user.id, application_id, payload.topic_slug, payload.is_reviewed)


# ---------------------------------------------------------------------------
# STAR stories
# ---------------------------------------------------------------------------

star_router = APIRouter()


@star_router.get("", response_model=list[StarStoryOut])
async def list_star_stories(
    category: str | None = None, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[StarStoryOut]:
    return await InterviewService(db).list_star_stories(user.id, category)


@star_router.post("", response_model=StarStoryOut, status_code=201)
async def create_star_story(
    payload: StarStoryCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> StarStoryOut:
    return await InterviewService(db).create_star_story(user.id, payload)


@star_router.get("/{story_id}", response_model=StarStoryOut)
async def get_star_story(
    story_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> StarStoryOut:
    return await InterviewService(db).get_star_story(user.id, story_id)


@star_router.put("/{story_id}", response_model=StarStoryOut)
async def update_star_story(
    story_id: str, payload: StarStoryUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> StarStoryOut:
    return await InterviewService(db).update_star_story(user.id, story_id, payload)


@star_router.delete("/{story_id}", status_code=204)
async def delete_star_story(
    story_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await InterviewService(db).delete_star_story(user.id, story_id)
