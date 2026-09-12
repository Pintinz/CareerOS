import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import (
    InterviewDifficulty,
    InterviewQuestion,
    InterviewQuestionCategory,
    InterviewTopic,
)


class InterviewCategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self) -> list[InterviewQuestionCategory]:
        result = await self.db.execute(select(InterviewQuestionCategory).order_by(InterviewQuestionCategory.name))
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> InterviewQuestionCategory | None:
        result = await self.db.execute(
            select(InterviewQuestionCategory).where(InterviewQuestionCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> InterviewQuestionCategory | None:
        result = await self.db.execute(
            select(InterviewQuestionCategory).where(InterviewQuestionCategory.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(self, category: InterviewQuestionCategory) -> InterviewQuestionCategory:
        self.db.add(category)
        await self.db.flush()
        return category


class InterviewTopicRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, *, category_id: str | None = None) -> list[InterviewTopic]:
        query = select(InterviewTopic)
        if category_id:
            query = query.where(InterviewTopic.category_id == category_id)
        result = await self.db.execute(query.order_by(InterviewTopic.name))
        return list(result.scalars().all())

    async def get_by_id(self, topic_id: str) -> InterviewTopic | None:
        result = await self.db.execute(select(InterviewTopic).where(InterviewTopic.id == topic_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> InterviewTopic | None:
        result = await self.db.execute(select(InterviewTopic).where(InterviewTopic.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, topic: InterviewTopic) -> InterviewTopic:
        self.db.add(topic)
        await self.db.flush()
        return topic


class InterviewQuestionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, question_id: str) -> InterviewQuestion | None:
        result = await self.db.execute(select(InterviewQuestion).where(InterviewQuestion.id == question_id))
        return result.scalar_one_or_none()

    async def list_admin(
        self, *, page: int, page_size: int, category_id: str | None = None, search: str | None = None
    ) -> tuple[list[InterviewQuestion], int]:
        query = select(InterviewQuestion)
        count_query = select(func.count()).select_from(InterviewQuestion)
        if category_id:
            query = query.where(InterviewQuestion.category_id == category_id)
            count_query = count_query.where(InterviewQuestion.category_id == category_id)
        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(func.lower(InterviewQuestion.question_text).like(pattern))
            count_query = count_query.where(func.lower(InterviewQuestion.question_text).like(pattern))

        query = query.order_by(InterviewQuestion.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def create(self, question: InterviewQuestion) -> InterviewQuestion:
        self.db.add(question)
        await self.db.flush()
        return question

    async def delete(self, question: InterviewQuestion) -> None:
        await self.db.delete(question)

    async def candidates_for_selection(
        self,
        *,
        category_ids: list[str] | None,
        difficulty: InterviewDifficulty | None,
        exclude_difficulties: list[InterviewDifficulty] | None = None,
        topic_slugs: list[str] | None = None,
        company_id: str | None = None,
        exclude_ids: set[str] | None = None,
    ) -> list[InterviewQuestion]:
        """All active questions matching the filters, for the generation engine to sample from."""
        query = select(InterviewQuestion).where(InterviewQuestion.is_active.is_(True))
        if category_ids:
            query = query.where(InterviewQuestion.category_id.in_(category_ids))
        if difficulty:
            query = query.where(InterviewQuestion.difficulty == difficulty)
        if exclude_difficulties:
            query = query.where(InterviewQuestion.difficulty.notin_(exclude_difficulties))
        if company_id:
            query = query.where(InterviewQuestion.company_id == company_id)
        if exclude_ids:
            query = query.where(InterviewQuestion.id.notin_(exclude_ids))
        if topic_slugs:
            query = query.join(InterviewTopic, InterviewQuestion.topic_id == InterviewTopic.id).where(
                InterviewTopic.slug.in_(topic_slugs)
            )

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())


def sample_without_replacement(items: list[InterviewQuestion], count: int) -> list[InterviewQuestion]:
    if len(items) <= count:
        return list(items)
    return random.sample(items, count)
