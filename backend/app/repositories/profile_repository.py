from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile


class ProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: str) -> Profile | None:
        result = await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_empty(self, user_id: str) -> Profile:
        profile = Profile(user_id=user_id)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def update(self, profile: Profile, **fields: object) -> Profile:
        for key, value in fields.items():
            if value is not None:
                setattr(profile, key, value)
        await self.db.flush()
        return profile
