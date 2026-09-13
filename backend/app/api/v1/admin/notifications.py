from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.admin_ops import AdminNotificationCreate, AdminNotificationOut
from app.schemas.pagination import PaginatedResponse
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
from app.services.admin_ops_service import NotificationService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)


class AdminNotificationListResponse(PaginatedResponse[AdminNotificationOut]):
    pass


@router.get("", response_model=AdminNotificationListResponse, dependencies=[Depends(_CAN_READ)])
async def list_notifications(
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), db: AsyncSession = Depends(get_db)
) -> AdminNotificationListResponse:
    items, total = await NotificationService(db).list_admin(page=page, page_size=page_size)
    return AdminNotificationListResponse(
        items=[AdminNotificationOut.model_validate(n) for n in items], page=page, page_size=page_size, total=total
    )


@router.post("", response_model=AdminNotificationOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_CAN_WRITE)])
async def create_notification(
    payload: AdminNotificationCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> AdminNotificationOut:
    notification = await NotificationService(db).create(payload, admin_id=admin.id)
    await audit_service.record(db, admin_id=admin.id, action="create", entity_type="notification", entity_id=notification.id)
    return AdminNotificationOut.model_validate(notification)


@router.post("/{notification_id}/send", response_model=AdminNotificationOut, dependencies=[Depends(_CAN_WRITE)])
async def send_notification(
    notification_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> AdminNotificationOut:
    notification = await NotificationService(db).send_now(notification_id)
    await audit_service.record(db, admin_id=admin.id, action="send", entity_type="notification", entity_id=notification_id)
    return AdminNotificationOut.model_validate(notification)
