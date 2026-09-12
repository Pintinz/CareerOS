from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.models.job import ContentStatus
from app.schemas.intelligence import (
    IntelligenceAdminListResponse,
    IntelligenceAdminOut,
    IntelligenceCreate,
    IntelligenceUpdate,
)
from app.security.admin_dependencies import require_admin_role
from app.services.intelligence_service import IntelligenceService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(
    AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER
)


@router.get("", response_model=IntelligenceAdminListResponse, dependencies=[Depends(_CAN_READ)])
async def list_intelligence_admin(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    post_status: ContentStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> IntelligenceAdminListResponse:
    items, total = await IntelligenceService(db).list_admin(
        page=page, page_size=page_size, search=search, post_status=post_status
    )
    return IntelligenceAdminListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{post_id}", response_model=IntelligenceAdminOut, dependencies=[Depends(_CAN_READ)])
async def get_intelligence_admin(post_id: str, db: AsyncSession = Depends(get_db)) -> IntelligenceAdminOut:
    service = IntelligenceService(db)
    post = await service.get_for_admin(post_id)
    return await service.to_admin(post)


@router.post(
    "",
    response_model=IntelligenceAdminOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_CAN_WRITE)],
)
async def create_intelligence(payload: IntelligenceCreate, db: AsyncSession = Depends(get_db)) -> IntelligenceAdminOut:
    return await IntelligenceService(db).create(payload)


@router.put("/{post_id}", response_model=IntelligenceAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def update_intelligence(
    post_id: str, payload: IntelligenceUpdate, db: AsyncSession = Depends(get_db)
) -> IntelligenceAdminOut:
    return await IntelligenceService(db).update(post_id, payload)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_intelligence(post_id: str, db: AsyncSession = Depends(get_db)) -> None:
    await IntelligenceService(db).delete(post_id)
