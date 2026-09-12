from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_session import TestAnswer, TestSession, TestSessionQuestion


class TestSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, session: TestSession) -> TestSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_owned(self, session_id: str, user_id: str) -> TestSession | None:
        result = await self.db.execute(
            select(TestSession).where(TestSession.id == session_id, TestSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, *, page: int, page_size: int, status: str | None = None
    ) -> tuple[list[TestSession], int]:
        query = select(TestSession).where(TestSession.user_id == user_id)
        count_query = select(func.count()).select_from(TestSession).where(TestSession.user_id == user_id)
        if status:
            query = query.where(TestSession.status == status)
            count_query = count_query.where(TestSession.status == status)

        query = query.order_by(TestSession.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def list_submitted_for_user(self, user_id: str) -> list[TestSession]:
        result = await self.db.execute(
            select(TestSession)
            .where(TestSession.user_id == user_id, TestSession.status.in_(["SUBMITTED", "AUTO_SUBMITTED"]))
            .order_by(TestSession.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def add_question(self, session_question: TestSessionQuestion) -> TestSessionQuestion:
        self.db.add(session_question)
        await self.db.flush()
        return session_question

    async def get_session_questions(self, session_id: str) -> list[TestSessionQuestion]:
        result = await self.db.execute(
            select(TestSessionQuestion)
            .where(TestSessionQuestion.session_id == session_id)
            .order_by(TestSessionQuestion.order_index)
        )
        return list(result.scalars().all())

    async def get_session_question(self, session_id: str, session_question_id: str) -> TestSessionQuestion | None:
        result = await self.db.execute(
            select(TestSessionQuestion).where(
                TestSessionQuestion.id == session_question_id, TestSessionQuestion.session_id == session_id
            )
        )
        return result.scalar_one_or_none()

    async def get_answer(self, session_question_id: str) -> TestAnswer | None:
        result = await self.db.execute(
            select(TestAnswer).where(TestAnswer.session_question_id == session_question_id)
        )
        return result.scalar_one_or_none()

    async def get_answers_for_session(self, session_id: str) -> list[TestAnswer]:
        result = await self.db.execute(select(TestAnswer).where(TestAnswer.session_id == session_id))
        return list(result.scalars().all())

    async def upsert_answer(self, answer: TestAnswer) -> TestAnswer:
        self.db.add(answer)
        await self.db.flush()
        return answer
