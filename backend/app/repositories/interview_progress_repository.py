from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewPreparationProgress


class InterviewProgressRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, user_id: str, application_id: str | None) -> InterviewPreparationProgress:
        query = select(InterviewPreparationProgress).where(InterviewPreparationProgress.user_id == user_id)
        query = (
            query.where(InterviewPreparationProgress.application_id == application_id)
            if application_id
            else query.where(InterviewPreparationProgress.application_id.is_(None))
        )
        result = await self.db.execute(query)
        progress = result.scalar_one_or_none()
        if progress is not None:
            return progress

        from app.interview.checklist import default_checklist

        progress = InterviewPreparationProgress(
            user_id=user_id, application_id=application_id, checklist=default_checklist(), questions_to_ask=[], reviewed_topics=[]
        )
        self.db.add(progress)
        await self.db.flush()
        return progress

    async def list_for_user(self, user_id: str) -> list[InterviewPreparationProgress]:
        result = await self.db.execute(
            select(InterviewPreparationProgress).where(InterviewPreparationProgress.user_id == user_id)
        )
        return list(result.scalars().all())
