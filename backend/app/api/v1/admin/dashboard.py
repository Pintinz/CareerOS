from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.security.admin_dependencies import require_admin_role
from app.services.dashboard_service import get_dashboard, get_operations

router = APIRouter()

_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)


@router.get("", dependencies=[Depends(_CAN_READ)])
async def dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    return await get_dashboard(db)


@router.get("/operations", dependencies=[Depends(_CAN_READ)])
async def operations(db: AsyncSession = Depends(get_db)) -> dict:
    return await get_operations(db)
