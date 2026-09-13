from fastapi import APIRouter, Depends, File, Query, UploadFile, status
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
from app.services import audit_service
from app.services.aptitude_service import AptitudeService
from app.services.question_import_service import import_aptitude_questions

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
    question = await AptitudeService(db).admin_create_question(payload, admin.id)
    await audit_service.record(db, admin_id=admin.id, action="create", entity_type="aptitude_question", entity_id=question.id)
    return question


@router.put("/questions/{question_id}", response_model=QuestionAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def update_question_admin(
    question_id: str, payload: QuestionUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)
) -> QuestionAdminOut:
    question = await AptitudeService(db).admin_update_question(question_id, payload)
    await audit_service.record(db, admin_id=admin.id, action="update", entity_type="aptitude_question", entity_id=question_id)
    return question


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_question_admin(
    question_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))
) -> None:
    await AptitudeService(db).admin_delete_question(question_id)
    await audit_service.record(db, admin_id=admin.id, action="delete", entity_type="aptitude_question", entity_id=question_id)


@router.post("/questions/bulk-import", dependencies=[Depends(_CAN_WRITE)])
async def bulk_import_questions_admin(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)
) -> dict:
    """Spec §20-21 — CSV columns: question_text, question_type, category_slug, topic_slug, field,
    industry, job_role, difficulty, explanation, marks, negative_marks,
    option_1..4 + option_1..4_correct (true/false). Every row is validated independently; a
    broken row is reported with its reason and never imported."""
    csv_text = (await file.read()).decode("utf-8-sig")
    result = await import_aptitude_questions(db, csv_text, admin_id=admin.id)
    await audit_service.record(
        db, admin_id=admin.id, action="bulk_import", entity_type="aptitude_question",
        metadata={"imported": result.imported, "skipped": result.skipped, "errors": len(result.errors)},
    )
    return {"imported": result.imported, "skipped": result.skipped, "errors": result.errors, "duplicate_warnings": result.duplicate_warnings}
