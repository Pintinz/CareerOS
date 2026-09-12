from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.aptitude import (
    QuestionAdminListResponse,
    QuestionAdminOut,
    QuestionCategoryCreate,
    QuestionCategoryOut,
    QuestionCreate,
    QuestionTopicCreate,
    QuestionTopicOut,
    QuestionUpdate,
)
from app.security.admin_dependencies import get_current_admin, require_admin_role
from app.services.aptitude_service import AptitudeService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(
    AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER
)


@router.get("/categories", response_model=list[QuestionCategoryOut], dependencies=[Depends(_CAN_READ)])
async def list_categories_admin(db: AsyncSession = Depends(get_db)) -> list[QuestionCategoryOut]:
    categories = await AptitudeService(db).admin_list_categories()
    return [QuestionCategoryOut.model_validate(c) for c in categories]


@router.post(
    "/categories",
    response_model=QuestionCategoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_CAN_WRITE)],
)
async def create_category_admin(
    payload: QuestionCategoryCreate, db: AsyncSession = Depends(get_db)
) -> QuestionCategoryOut:
    category = await AptitudeService(db).admin_create_category(payload)
    return QuestionCategoryOut.model_validate(category)


@router.get("/topics", response_model=list[QuestionTopicOut], dependencies=[Depends(_CAN_READ)])
async def list_topics_admin(
    category_id: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[QuestionTopicOut]:
    topics = await AptitudeService(db).admin_list_topics(category_id)
    return [QuestionTopicOut.model_validate(t) for t in topics]


@router.post(
    "/topics", response_model=QuestionTopicOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_CAN_WRITE)]
)
async def create_topic_admin(payload: QuestionTopicCreate, db: AsyncSession = Depends(get_db)) -> QuestionTopicOut:
    topic = await AptitudeService(db).admin_create_topic(payload)
    return QuestionTopicOut.model_validate(topic)


@router.get("/questions", response_model=QuestionAdminListResponse, dependencies=[Depends(_CAN_READ)])
async def list_questions_admin(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> QuestionAdminListResponse:
    items, total = await AptitudeService(db).admin_list_questions(
        page=page, page_size=page_size, category_id=category_id, search=search
    )
    return QuestionAdminListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/questions/{question_id}", response_model=QuestionAdminOut, dependencies=[Depends(_CAN_READ)])
async def get_question_admin(question_id: str, db: AsyncSession = Depends(get_db)) -> QuestionAdminOut:
    return await AptitudeService(db).admin_get_question(question_id)


@router.post(
    "/questions",
    response_model=QuestionAdminOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_CAN_WRITE)],
)
async def create_question_admin(
    payload: QuestionCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)
) -> QuestionAdminOut:
    return await AptitudeService(db).admin_create_question(payload, admin.id)


@router.put("/questions/{question_id}", response_model=QuestionAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def update_question_admin(
    question_id: str, payload: QuestionUpdate, db: AsyncSession = Depends(get_db)
) -> QuestionAdminOut:
    return await AptitudeService(db).admin_update_question(question_id, payload)


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_question_admin(question_id: str, db: AsyncSession = Depends(get_db)) -> None:
    await AptitudeService(db).admin_delete_question(question_id)
