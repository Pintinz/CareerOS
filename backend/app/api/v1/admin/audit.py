from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.schemas.admin_ops import AuditLogListResponse, AuditLogOut
from app.security.admin_dependencies import require_admin_role
from app.services.admin_ops_service import AuditLogService

router = APIRouter()

_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN)


@router.get("", response_model=AuditLogListResponse, dependencies=[Depends(_CAN_READ)])
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    entity_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    items, total = await AuditLogService(db).list_admin(page=page, page_size=page_size, entity_type=entity_type)
    return AuditLogListResponse(
        items=[AuditLogOut.model_validate(i) for i in items], page=page, page_size=page_size, total=total
    )
