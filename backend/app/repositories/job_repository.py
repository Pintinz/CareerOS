from datetime import datetime, timedelta, timezone

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slugify import slugify
from app.models.company import Company
from app.models.job import ContentStatus, EmploymentType, Job, OpportunityType, SavedJob, SourceState


class JobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, job_id: str) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id_or_slug(self, id_or_slug: str) -> Job | None:
        return await self.get_by_id(id_or_slug) or await self.get_by_slug(id_or_slug)

    async def generate_unique_slug(self, title: str, company_name: str) -> str:
        base_slug = slugify(f"{title}-{company_name}")
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
        location: str | None = None,
        industry: str | None = None,
        employment_type: str | None = None,
        work_mode: str | None = None,
        experience_level: str | None = None,
        is_featured: bool | None = None,
        company_id: str | None = None,
        opportunity_type: str | None = None,
        posted_within_days: int | None = None,
        sort: str = "newest",
    ) -> tuple[list[Job], int]:
        now = datetime.now(timezone.utc)
        base_conditions = [
            Job.status == ContentStatus.PUBLISHED,
            Job.is_active.is_(True),
            # A job past its own expiry date or deadline shouldn't surface even if an admin forgot
            # to archive it — never rely solely on manual status changes for this.
            or_(Job.expires_at.is_(None), Job.expires_at > now),
            or_(Job.application_deadline.is_(None), Job.application_deadline > now),
            # Listings whose source removed or closed them stay out of feeds (detail stays reachable).
            Job.source_state == SourceState.ACTIVE,
        ]

        query = select(Job).join(Company, Job.company_id == Company.id)
        count_query = select(func.count()).select_from(Job).join(Company, Job.company_id == Company.id)

        for condition in base_conditions:
            query = query.where(condition)
            count_query = count_query.where(condition)

        filters = []
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(Job.title).like(pattern),
                    func.lower(Company.name).like(pattern),
                    func.lower(Job.location).like(pattern),
                    func.lower(cast(Job.preferred_skills, String)).like(pattern),
                )
            )
        if country:
            filters.append(func.lower(Job.country) == country.lower())
        if location:
            filters.append(func.lower(Job.location).like(f"%{location.lower()}%"))
        if industry:
            filters.append(func.lower(Job.industry) == industry.lower())
        if employment_type:
            filters.append(Job.employment_type == employment_type)
        if work_mode:
            filters.append(Job.work_mode == work_mode)
        if experience_level:
            filters.append(Job.experience_level == experience_level)
        if is_featured is not None:
            filters.append(Job.is_featured.is_(is_featured))
        if company_id:
            filters.append(Job.company_id == company_id)
        if opportunity_type == OpportunityType.INTERNSHIP or opportunity_type == "INTERNSHIP":
            # Manually authored internships predate opportunity_type and carry only the employment type.
            filters.append(or_(Job.opportunity_type == OpportunityType.INTERNSHIP, Job.employment_type == EmploymentType.INTERNSHIP))
        elif opportunity_type:
            filters.append(Job.opportunity_type == opportunity_type)
        if posted_within_days:
            filters.append(Job.published_at >= now - timedelta(days=posted_within_days))

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        if sort == "deadline":
            query = query.order_by(Job.application_deadline.asc().nulls_last())
        elif sort == "recommended":
            # Deterministic proxy until the real matching engine (Phase 3+) lands: featured
            # first, then newest. Never a random or fabricated "recommended" order.
            query = query.order_by(Job.is_featured.desc(), Job.published_at.desc())
        else:  # newest
            query = query.order_by(Job.published_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)

        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().unique().all()
        return list(items), total

    async def list_admin(
        self, *, page: int, page_size: int, search: str | None = None, status: str | None = None
    ) -> tuple[list[Job], int]:
        query = select(Job)
        count_query = select(func.count()).select_from(Job)

        if status:
            query = query.where(Job.status == status)
            count_query = count_query.where(Job.status == status)
        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(func.lower(Job.title).like(pattern))
            count_query = count_query.where(func.lower(Job.title).like(pattern))

        query = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def create(self, job: Job) -> Job:
        self.db.add(job)
        await self.db.flush()
        return job

    async def delete(self, job: Job) -> None:
        await self.db.delete(job)

    # --- saved jobs ---

    async def get_saved(self, user_id: str, job_id: str) -> SavedJob | None:
        result = await self.db.execute(
            select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def save_job(self, user_id: str, job_id: str) -> SavedJob:
        existing = await self.get_saved(user_id, job_id)
        if existing:
            return existing
        saved = SavedJob(user_id=user_id, job_id=job_id)
        self.db.add(saved)
        await self.db.flush()
        return saved

    async def unsave_job(self, user_id: str, job_id: str) -> None:
        existing = await self.get_saved(user_id, job_id)
        if existing:
            await self.db.delete(existing)

    async def list_saved_job_ids(self, user_id: str) -> set[str]:
        result = await self.db.execute(select(SavedJob.job_id).where(SavedJob.user_id == user_id))
        return set(result.scalars().all())

    async def list_saved_jobs(self, user_id: str, *, page: int, page_size: int) -> tuple[list[Job], int]:
        query = (
            select(Job)
            .join(SavedJob, SavedJob.job_id == Job.id)
            .where(SavedJob.user_id == user_id)
            .order_by(SavedJob.created_at.desc())
        )
        count_query = select(func.count()).select_from(SavedJob).where(SavedJob.user_id == user_id)

        total = (await self.db.execute(count_query)).scalar_one()
        items = (
            (await self.db.execute(query.offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )
        return list(items), total
