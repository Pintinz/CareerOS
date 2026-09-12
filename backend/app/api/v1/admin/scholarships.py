from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.models.job import ContentStatus
from app.schemas.scholarship import (
    ScholarshipAdminListResponse,
    ScholarshipAdminOut,
    ScholarshipCreate,
    ScholarshipUpdate,
)
from app.security.admin_dependencies import require_admin_role
from app.services.scholarship_service import ScholarshipService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(
    AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER
)


@router.get("", response_model=ScholarshipAdminListResponse, dependencies=[Depends(_CAN_READ)])
async def list_scholarships_admin(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    scholarship_status: ContentStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> ScholarshipAdminListResponse:
    items, total = await ScholarshipService(db).list_admin(
        page=page, page_size=page_size, search=search, scholarship_status=scholarship_status
    )
    return ScholarshipAdminListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{scholarship_id}", response_model=ScholarshipAdminOut, dependencies=[Depends(_CAN_READ)])
async def get_scholarship_admin(scholarship_id: str, db: AsyncSession = Depends(get_db)) -> ScholarshipAdminOut:
    service = ScholarshipService(db)
    scholarship = await service.get_for_admin(scholarship_id)
    return service.to_admin(scholarship)


@router.post(
    "",
    response_model=ScholarshipAdminOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_CAN_WRITE)],
)
async def create_scholarship(
    payload: ScholarshipCreate, db: AsyncSession = Depends(get_db)
) -> ScholarshipAdminOut:
    return await ScholarshipService(db).create(payload)


@router.put("/{scholarship_id}", response_model=ScholarshipAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def update_scholarship(
    scholarship_id: str, payload: ScholarshipUpdate, db: AsyncSession = Depends(get_db)
) -> ScholarshipAdminOut:
    return await ScholarshipService(db).update(scholarship_id, payload)


@router.delete(
    "/{scholarship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_scholarship(scholarship_id: str, db: AsyncSession = Depends(get_db)) -> None:
    await ScholarshipService(db).delete(scholarship_id)
