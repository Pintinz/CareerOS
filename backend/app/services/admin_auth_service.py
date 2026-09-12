from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole, AdminUser
from app.repositories.admin_user_repository import AdminUserRepository
from app.schemas.auth import TokenResponse
from app.security.jwt import TokenAudience, create_access_token, create_refresh_token
from app.security.password import hash_password, verify_password


class AdminAuthService:
    """Deliberately has no public self-registration endpoint — admin accounts are created by
    an existing SUPER_ADMIN (once that flow is built) or via `ensure_seed_admin` on first run."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.admins = AdminUserRepository(db)

    async def authenticate(self, *, email: str, password: str) -> AdminUser:
        invalid_credentials = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )

        admin = await self.admins.get_by_email(email)
        if admin is None or not verify_password(password, admin.hashed_password):
            raise invalid_credentials
        if not admin.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is disabled")

        return admin

    def issue_tokens(self, admin: AdminUser) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(admin.id, audience=TokenAudience.ADMIN),
            refresh_token=create_refresh_token(admin.id, audience=TokenAudience.ADMIN),
        )


async def ensure_seed_admin(db: AsyncSession, *, email: str | None, password: str | None) -> None:
    """Creates the first SUPER_ADMIN from env-configured credentials if no admin exists yet.
    No-op if credentials aren't set or an admin already exists — never overwrites/resets one."""
    if not email or not password:
        return

    repo = AdminUserRepository(db)
    if await repo.count() > 0:
        return

    await repo.create(email=email, hashed_password=hash_password(password), role=AdminRole.SUPER_ADMIN)
    await db.commit()
