from datetime import datetime, timedelta, timezone

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slugify import slugify
from app.models.job import ContentStatus, SourceState
from app.models.scholarship import SavedScholarship, Scholarship


class ScholarshipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, scholarship_id: str) -> Scholarship | None:
        result = await self.db.execute(select(Scholarship).where(Scholarship.id == scholarship_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Scholarship | None:
        result = await self.db.execute(select(Scholarship).where(Scholarship.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id_or_slug(self, id_or_slug: str) -> Scholarship | None:
        return await self.get_by_id(id_or_slug) or await self.get_by_slug(id_or_slug)

    async def generate_unique_slug(self, name: str) -> str:
        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while await self.get_by_slug(slug) is not None:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    async def list_public(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        country: str | None = None,
        degree_level: str | None = None,
        funding_type: str | None = None,
        award_type: str | None = None,
        field_of_study: str | None = None,
        deadline_within_days: int | None = None,
    ) -> tuple[list[Scholarship], int]:
        now = datetime.now(timezone.utc)
        base_conditions = [
            Scholarship.status == ContentStatus.PUBLISHED,
            Scholarship.is_active.is_(True),
            Scholarship.source_state == SourceState.ACTIVE,
            or_(Scholarship.application_deadline.is_(None), Scholarship.application_deadline > now),
        ]

        query = select(Scholarship)
        count_query = select(func.count()).select_from(Scholarship)
        for condition in base_conditions:
            query = query.where(condition)
            count_query = count_query.where(condition)

        if search:
            pattern = f"%{search.lower()}%"
            condition = or_(
                func.lower(Scholarship.name).like(pattern),
                func.lower(Scholarship.organization).like(pattern),
                func.lower(Scholarship.country).like(pattern),
                func.lower(cast(Scholarship.fields_of_study, String)).like(pattern),
            )
            query = query.where(condition)
            count_query = count_query.where(condition)
        if country:
            query = query.where(func.lower(Scholarship.country) == country.lower())
            count_query = count_query.where(func.lower(Scholarship.country) == country.lower())
        if funding_type:
            query = query.where(Scholarship.funding_type == funding_type)
            count_query = count_query.where(Scholarship.funding_type == funding_type)
        if award_type:
            query = query.where(Scholarship.award_type == award_type)
            count_query = count_query.where(Scholarship.award_type == award_type)
        if field_of_study:
            condition = func.lower(cast(Scholarship.fields_of_study, String)).like(f"%{field_of_study.lower()}%")
            query = query.where(condition)
            count_query = count_query.where(condition)
        if deadline_within_days:
            condition = Scholarship.application_deadline <= now + timedelta(days=deadline_within_days)
            query = query.where(condition)
            count_query = count_query.where(condition)
        if degree_level:
            # `degree_levels` is a JSON list column. This does a substring match on its text
            # representation (portable across SQLite/Postgres) rather than a real JSON
            # containment query — good enough at this scale; revisit with Postgres JSONB
            # `@>` once the dataset is large enough for it to matter.
            pattern = f'%"{degree_level.upper()}"%'
            condition = cast(Scholarship.degree_levels, String).like(pattern)
            query = query.where(condition)
            count_query = count_query.where(condition)

        query = query.order_by(Scholarship.published_at.desc()).offset((page - 1) * page_size).limit(page_size)

        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def list_admin(
        self, *, page: int, page_size: int, search: str | None = None, status: str | None = None
    ) -> tuple[list[Scholarship], int]:
        query = select(Scholarship)
        count_query = select(func.count()).select_from(Scholarship)
        if status:
            query = query.where(Scholarship.status == status)
            count_query = count_query.where(Scholarship.status == status)
        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(func.lower(Scholarship.name).like(pattern))
            count_query = count_query.where(func.lower(Scholarship.name).like(pattern))

        query = query.order_by(Scholarship.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def create(self, scholarship: Scholarship) -> Scholarship:
        self.db.add(scholarship)
        await self.db.flush()
        return scholarship

    async def delete(self, scholarship: Scholarship) -> None:
        await self.db.delete(scholarship)

    # --- saved scholarships ---

    async def get_saved(self, user_id: str, scholarship_id: str) -> SavedScholarship | None:
        result = await self.db.execute(
            select(SavedScholarship).where(
                SavedScholarship.user_id == user_id, SavedScholarship.scholarship_id == scholarship_id
            )
        )
        return result.scalar_one_or_none()

    async def save(self, user_id: str, scholarship_id: str) -> SavedScholarship:
        existing = await self.get_saved(user_id, scholarship_id)
        if existing:
            return existing
        saved = SavedScholarship(user_id=user_id, scholarship_id=scholarship_id)
        self.db.add(saved)
        await self.db.flush()
        return saved

    async def unsave(self, user_id: str, scholarship_id: str) -> None:
        existing = await self.get_saved(user_id, scholarship_id)
        if existing:
            await self.db.delete(existing)

    async def list_saved_ids(self, user_id: str) -> set[str]:
        result = await self.db.execute(
            select(SavedScholarship.scholarship_id).where(SavedScholarship.user_id == user_id)
        )
        return set(result.scalars().all())

    async def list_saved(
        self, user_id: str, *, page: int, page_size: int
    ) -> tuple[list[Scholarship], int]:
        query = (
            select(Scholarship)
            .join(SavedScholarship, SavedScholarship.scholarship_id == Scholarship.id)
            .where(SavedScholarship.user_id == user_id)
            .order_by(SavedScholarship.created_at.desc())
        )
        count_query = (
            select(func.count()).select_from(SavedScholarship).where(SavedScholarship.user_id == user_id)
        )
        total = (await self.db.execute(count_query)).scalar_one()
        items = (
            (await self.db.execute(query.offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )
        return list(items), total
