from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole, AdminUser


class AdminUserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> AdminUser | None:
        result = await self.db.execute(select(AdminUser).where(AdminUser.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_id(self, admin_id: str) -> AdminUser | None:
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.db.execute(select(AdminUser))
        return len(result.scalars().all())

    async def create(self, *, email: str, hashed_password: str, role: AdminRole) -> AdminUser:
        admin = AdminUser(email=email.lower(), hashed_password=hashed_password, role=role)
        self.db.add(admin)
        await self.db.flush()
        return admin
