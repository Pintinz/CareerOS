from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewRecording


class InterviewRecordingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, recording: InterviewRecording) -> InterviewRecording:
        self.db.add(recording)
        return recording

    async def get_owned(self, recording_id: str, user_id: str) -> InterviewRecording | None:
        result = await self.db.execute(
            select(InterviewRecording).where(
                InterviewRecording.id == recording_id, InterviewRecording.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[InterviewRecording]:
        result = await self.db.execute(
            select(InterviewRecording)
            .where(InterviewRecording.user_id == user_id)
            .order_by(InterviewRecording.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, recording: InterviewRecording) -> None:
        await self.db.delete(recording)
