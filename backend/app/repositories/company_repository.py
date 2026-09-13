from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slugify import slugify
from app.models.company import Company


class CompanyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, company_id: str) -> Company | None:
        result = await self.db.execute(select(Company).where(Company.id == company_id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, company_ids: set[str]) -> dict[str, Company]:
        """Batch lookup keyed by id — avoids a separate SELECT per row when rendering a list of
        Jobs (Job has no ORM relationship to Company; see JobService._job_fields)."""
        if not company_ids:
            return {}
        result = await self.db.execute(select(Company).where(Company.id.in_(company_ids)))
        return {c.id: c for c in result.scalars().all()}

    async def get_by_slug(self, slug: str) -> Company | None:
        result = await self.db.execute(select(Company).where(Company.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id_or_slug(self, id_or_slug: str) -> Company | None:
        return await self.get_by_id(id_or_slug) or await self.get_by_slug(id_or_slug)

    async def get_by_name(self, name: str) -> Company | None:
        """Best-effort case-insensitive exact-name match — used only to resolve company-specific
        interview prep for a manually-entered application (no job_id, so no company_id) whose
        `company_name` happens to match a real company already in our database."""
        result = await self.db.execute(select(Company).where(func.lower(Company.name) == name.lower()))
        return result.scalars().first()

    async def generate_unique_slug(self, name: str) -> str:
        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while await self.get_by_slug(slug) is not None:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[Company], int]:
        query = select(Company)
        count_query = select(func.count()).select_from(Company)

        if active_only:
            query = query.where(Company.is_active.is_(True))
            count_query = count_query.where(Company.is_active.is_(True))

        if search:
            pattern = f"%{search.lower()}%"
            condition = or_(
                func.lower(Company.name).like(pattern),
                func.lower(Company.industry).like(pattern),
                func.lower(Company.country).like(pattern),
            )
            query = query.where(condition)
            count_query = count_query.where(condition)

        query = query.order_by(Company.name).offset((page - 1) * page_size).limit(page_size)

        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def create(self, company: Company) -> Company:
        self.db.add(company)
        await self.db.flush()
        return company

    async def delete(self, company: Company) -> None:
        await self.db.delete(company)
