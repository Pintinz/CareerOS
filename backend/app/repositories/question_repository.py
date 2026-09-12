import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question, QuestionCategory, QuestionDifficulty, QuestionOption, QuestionTopic


class QuestionCategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self) -> list[QuestionCategory]:
        result = await self.db.execute(select(QuestionCategory).order_by(QuestionCategory.name))
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> QuestionCategory | None:
        result = await self.db.execute(select(QuestionCategory).where(QuestionCategory.id == category_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> QuestionCategory | None:
        result = await self.db.execute(select(QuestionCategory).where(QuestionCategory.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, category: QuestionCategory) -> QuestionCategory:
        self.db.add(category)
        await self.db.flush()
        return category


class QuestionTopicRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, *, category_id: str | None = None) -> list[QuestionTopic]:
        query = select(QuestionTopic)
        if category_id:
            query = query.where(QuestionTopic.category_id == category_id)
        result = await self.db.execute(query.order_by(QuestionTopic.name))
        return list(result.scalars().all())

    async def get_by_id(self, topic_id: str) -> QuestionTopic | None:
        result = await self.db.execute(select(QuestionTopic).where(QuestionTopic.id == topic_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> QuestionTopic | None:
        result = await self.db.execute(select(QuestionTopic).where(QuestionTopic.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, topic: QuestionTopic) -> QuestionTopic:
        self.db.add(topic)
        await self.db.flush()
        return topic


class QuestionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, question_id: str) -> Question | None:
        result = await self.db.execute(select(Question).where(Question.id == question_id))
        return result.scalar_one_or_none()

    async def get_options(self, question_id: str) -> list[QuestionOption]:
        result = await self.db.execute(
            select(QuestionOption)
            .where(QuestionOption.question_id == question_id)
            .order_by(QuestionOption.display_order)
        )
        return list(result.scalars().all())

    async def list_admin(
        self, *, page: int, page_size: int, category_id: str | None = None, search: str | None = None
    ) -> tuple[list[Question], int]:
        query = select(Question)
        count_query = select(func.count()).select_from(Question)
        if category_id:
            query = query.where(Question.category_id == category_id)
            count_query = count_query.where(Question.category_id == category_id)
        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(func.lower(Question.question_text).like(pattern))
            count_query = count_query.where(func.lower(Question.question_text).like(pattern))

        query = query.order_by(Question.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def create(self, question: Question) -> Question:
        self.db.add(question)
        await self.db.flush()
        return question

    async def delete(self, question: Question) -> None:
        await self.db.delete(question)

    async def replace_options(self, question_id: str, options: list[QuestionOption]) -> None:
        existing = await self.get_options(question_id)
        for option in existing:
            await self.db.delete(option)
        await self.db.flush()
        for option in options:
            option.question_id = question_id
            self.db.add(option)
        await self.db.flush()

    async def candidates_for_selection(
        self,
        *,
        category_ids: list[str] | None,
        difficulty: QuestionDifficulty | None,
        topic_slugs: list[str] | None = None,
        exclude_ids: set[str] | None = None,
    ) -> list[Question]:
        """All active questions matching the filters, for the generation engine to sample from.
        `topic_slugs`, when given, restricts to those topics (used for job-specific technical
        selection) — callers fall back to the unfiltered category set if this returns too few."""
        query = select(Question).where(Question.is_active.is_(True))
        if category_ids:
            query = query.where(Question.category_id.in_(category_ids))
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
        if exclude_ids:
            query = query.where(Question.id.notin_(exclude_ids))
        if topic_slugs:
            query = query.join(QuestionTopic, Question.topic_id == QuestionTopic.id).where(
                QuestionTopic.slug.in_(topic_slugs)
            )

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())


def sample_without_replacement(items: list[Question], count: int) -> list[Question]:
    if len(items) <= count:
        return list(items)
    return random.sample(items, count)
