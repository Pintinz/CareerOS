from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import StarStory


class StarStoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, story: StarStory) -> StarStory:
        self.db.add(story)
        await self.db.flush()
        return story

    async def get_owned(self, story_id: str, user_id: str) -> StarStory | None:
        result = await self.db.execute(select(StarStory).where(StarStory.id == story_id, StarStory.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str, *, category: str | None = None) -> list[StarStory]:
        query = select(StarStory).where(StarStory.user_id == user_id)
        if category:
            query = query.where(StarStory.category == category)
        result = await self.db.execute(query.order_by(StarStory.updated_at.desc()))
        return list(result.scalars().all())

    async def delete(self, story: StarStory) -> None:
        await self.db.delete(story)
