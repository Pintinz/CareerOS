from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.test_session import TestStatus
from app.models.user import User
from app.repositories.question_repository import QuestionCategoryRepository, QuestionTopicRepository
from app.schemas.aptitude import (
    AnswerUpdate,
    AptitudeAnalyticsOut,
    QuestionCategoryOut,
    QuestionTopicOut,
    RecommendationsOut,
    ReviewOut,
    SessionQuestionOut,
    TestResultOut,
    TestSessionCreate,
    TestSessionDetailOut,
    TestSessionListResponse,
)
from app.security.dependencies import get_current_user
from app.services.aptitude_service import AptitudeService
from app.services.monetization_service import MonetizationService

router = APIRouter()


@router.get("/categories", response_model=list[QuestionCategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[QuestionCategoryOut]:
    categories = await QuestionCategoryRepository(db).list_all()
    return [QuestionCategoryOut.model_validate(c) for c in categories]


@router.get("/topics", response_model=list[QuestionTopicOut])
async def list_topics(
    category_id: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[QuestionTopicOut]:
    topics = await QuestionTopicRepository(db).list_all(category_id=category_id)
    return [QuestionTopicOut.model_validate(t) for t in topics]


@router.post("/sessions", response_model=TestSessionDetailOut, status_code=201)
async def create_session(
    payload: TestSessionCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> TestSessionDetailOut:
    await MonetizationService(db).enforce_aptitude_limit(user)
    return await AptitudeService(db).create_session(user.id, payload)


@router.get("/sessions", response_model=TestSessionListResponse)
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: TestStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TestSessionListResponse:
    items, total = await AptitudeService(db).list_for_user(
        user.id, page=page, page_size=page_size, status_filter=status_filter.value if status_filter else None
    )
    return TestSessionListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/sessions/{session_id}", response_model=TestSessionDetailOut)
async def get_session(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> TestSessionDetailOut:
    return await AptitudeService(db).get_session_detail(user.id, session_id)


@router.put("/sessions/{session_id}/answers/{question_id}", response_model=SessionQuestionOut)
async def update_answer(
    session_id: str,
    question_id: str,
    payload: AnswerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionQuestionOut:
    return await AptitudeService(db).update_answer(user.id, session_id, question_id, payload)


@router.post("/sessions/{session_id}/flag/{question_id}", response_model=SessionQuestionOut)
async def toggle_flag(
    session_id: str, question_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SessionQuestionOut:
    return await AptitudeService(db).toggle_flag(user.id, session_id, question_id)


@router.post("/sessions/{session_id}/submit", response_model=TestResultOut)
async def submit_session(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> TestResultOut:
    return await AptitudeService(db).submit(user.id, session_id)


@router.get("/sessions/{session_id}/results", response_model=TestResultOut)
async def get_results(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> TestResultOut:
    return await AptitudeService(db).get_result(user.id, session_id)


@router.get("/sessions/{session_id}/review", response_model=ReviewOut)
async def get_review(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ReviewOut:
    return await AptitudeService(db).get_review(user.id, session_id)


@router.get("/analytics", response_model=AptitudeAnalyticsOut)
async def get_analytics(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> AptitudeAnalyticsOut:
    return await AptitudeService(db).get_analytics(user.id)


@router.get("/recommendations", response_model=RecommendationsOut)
async def get_recommendations(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> RecommendationsOut:
    return await AptitudeService(db).get_recommendations(user.id)
