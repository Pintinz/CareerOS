from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.admin_ops import UserAdminListResponse, UserAdminOut
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
from app.services.admin_ops_service import UserAdminService

router = APIRouter()

_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)
# Spec §31: suspend/reactivate is SUPER_ADMIN (or explicitly permitted admins) only.
_CAN_SUSPEND = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN)


@router.get("", response_model=UserAdminListResponse, dependencies=[Depends(_CAN_READ)])
async def list_users_admin(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> UserAdminListResponse:
    items, total = await UserAdminService(db).list_admin(page=page, page_size=page_size, search=search)
    return UserAdminListResponse(items=items, page=page, page_size=page_size, total=total)


@router.post("/{user_id}/suspend", status_code=204, dependencies=[Depends(_CAN_SUSPEND)])
async def suspend_user(
    user_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_SUSPEND)
) -> None:
    await UserAdminService(db).set_active(user_id, is_active=False)
    await audit_service.record(db, admin_id=admin.id, action="suspend_user", entity_type="user", entity_id=user_id)


@router.post("/{user_id}/reactivate", status_code=204, dependencies=[Depends(_CAN_SUSPEND)])
async def reactivate_user(
    user_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_SUSPEND)
) -> None:
    await UserAdminService(db).set_active(user_id, is_active=True)
    await audit_service.record(db, admin_id=admin.id, action="reactivate_user", entity_type="user", entity_id=user_id)
