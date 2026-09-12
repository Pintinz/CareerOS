from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.application import ApplicationStage
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailOut,
    ApplicationListResponse,
    ApplicationNoteCreate,
    ApplicationNoteOut,
    ApplicationOut,
    ApplicationStageUpdate,
    ApplicationUpdate,
)
from app.security.dependencies import get_current_user
from app.services.application_service import ApplicationService

router = APIRouter()


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ApplicationOut:
    return await ApplicationService(db).create(user.id, payload)


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    stage: ApplicationStage | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationListResponse:
    items, total = await ApplicationService(db).list_for_user(user.id, page=page, page_size=page_size, stage=stage)
    return ApplicationListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{application_id}", response_model=ApplicationDetailOut)
async def get_application(
    application_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ApplicationDetailOut:
    return await ApplicationService(db).get_for_user(user.id, application_id)


@router.put("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationOut:
    return await ApplicationService(db).update(user.id, application_id, payload)


@router.post("/{application_id}/stage", response_model=ApplicationDetailOut)
async def update_application_stage(
    application_id: str,
    payload: ApplicationStageUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationDetailOut:
    return await ApplicationService(db).update_stage(user.id, application_id, payload)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await ApplicationService(db).delete(user.id, application_id)


@router.post("/{application_id}/notes", response_model=ApplicationNoteOut, status_code=status.HTTP_201_CREATED)
async def add_application_note(
    application_id: str,
    payload: ApplicationNoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationNoteOut:
    note = await ApplicationService(db).add_note(user.id, application_id, payload)
    return ApplicationNoteOut.model_validate(note)
