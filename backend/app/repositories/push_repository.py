from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push import DevicePlatform, DeviceToken, NotificationPreferences


class DeviceTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_platform_and_token(self, platform: DevicePlatform, token: str) -> DeviceToken | None:
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.platform == platform, DeviceToken.token == token)
        )
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: str) -> list[DeviceToken]:
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.user_id == user_id, DeviceToken.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def deactivate(self, user_id: str, token: str) -> None:
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.user_id == user_id, DeviceToken.token == token)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            row.is_active = False


class NotificationPreferencesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, user_id: str) -> NotificationPreferences:
        result = await self.db.execute(
            select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = NotificationPreferences(user_id=user_id)
            self.db.add(row)
            await self.db.flush()
        return row
