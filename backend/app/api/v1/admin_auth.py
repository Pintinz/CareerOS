from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminUser
from app.schemas.admin_auth import AdminLoginRequest, AdminTokenResponse, AdminUserOut
from app.security.admin_dependencies import get_current_admin
from app.security.rate_limit import admin_login_rate_limit
from app.services.admin_auth_service import AdminAuthService

router = APIRouter()


@router.post("/login", response_model=AdminTokenResponse, dependencies=[Depends(admin_login_rate_limit)])
async def admin_login(
    payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)
) -> AdminTokenResponse:
    service = AdminAuthService(db)
    admin = await service.authenticate(email=payload.email, password=payload.password)
    return service.issue_tokens(admin)


@router.get("/me", response_model=AdminUserOut)
async def read_current_admin(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    return admin
