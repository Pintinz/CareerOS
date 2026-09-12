from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewAnswer, InterviewSession, InterviewSessionQuestion, InterviewSessionStatus


class InterviewSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, session: InterviewSession) -> InterviewSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_owned(self, session_id: str, user_id: str) -> InterviewSession | None:
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, *, page: int, page_size: int, status: str | None = None
    ) -> tuple[list[InterviewSession], int]:
        query = select(InterviewSession).where(InterviewSession.user_id == user_id)
        count_query = select(func.count()).select_from(InterviewSession).where(InterviewSession.user_id == user_id)
        if status:
            query = query.where(InterviewSession.status == status)
            count_query = count_query.where(InterviewSession.status == status)

        query = query.order_by(InterviewSession.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def list_completed_for_user(self, user_id: str) -> list[InterviewSession]:
        result = await self.db.execute(
            select(InterviewSession)
            .where(InterviewSession.user_id == user_id, InterviewSession.status == InterviewSessionStatus.COMPLETED)
            .order_by(InterviewSession.completed_at.desc())
        )
        return list(result.scalars().all())

    async def add_question(self, session_question: InterviewSessionQuestion) -> InterviewSessionQuestion:
        self.db.add(session_question)
        await self.db.flush()
        return session_question

    async def get_session_questions(self, session_id: str) -> list[InterviewSessionQuestion]:
        result = await self.db.execute(
            select(InterviewSessionQuestion)
            .where(InterviewSessionQuestion.session_id == session_id)
            .order_by(InterviewSessionQuestion.order_index)
        )
        return list(result.scalars().all())

    async def get_session_question(self, session_id: str, session_question_id: str) -> InterviewSessionQuestion | None:
        result = await self.db.execute(
            select(InterviewSessionQuestion).where(
                InterviewSessionQuestion.id == session_question_id,
                InterviewSessionQuestion.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_answer(self, session_question_id: str) -> InterviewAnswer | None:
        result = await self.db.execute(
            select(InterviewAnswer).where(InterviewAnswer.session_question_id == session_question_id)
        )
        return result.scalar_one_or_none()

    async def get_answers_for_session(self, session_id: str) -> list[InterviewAnswer]:
        result = await self.db.execute(select(InterviewAnswer).where(InterviewAnswer.session_id == session_id))
        return list(result.scalars().all())

    async def upsert_answer(self, answer: InterviewAnswer) -> InterviewAnswer:
        self.db.add(answer)
        await self.db.flush()
        return answer
