from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ContentStatus, Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.company import CompanyOut
from app.services.availability import availability_of, is_official_source, publicly_listable, publicly_viewable
from app.schemas.job import (
    JobAdminOut,
    JobCardOut,
    JobCompanySummary,
    JobCreate,
    JobDetailOut,
    JobUpdate,
)


class JobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.jobs = JobRepository(db)
        self.companies = CompanyRepository(db)

    @staticmethod
    def _job_fields(job: Job, exclude: set[str]) -> dict:
        """`company` isn't an ORM relationship on Job (looked up separately), so it can't go
        through `Model.model_validate(job)` directly — build the field dict by hand instead."""
        return {
            name: getattr(job, name)
            for name in job.__table__.columns.keys()
            if name not in exclude
        }

    async def _require_company(self, company_id: str):
        company = await self.companies.get_by_id(company_id)
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Job has no valid company"
            )
        return company

    @staticmethod
    def _derived(job: Job) -> dict:
        return {"availability": availability_of(job), "is_official_source": is_official_source(job)}

    def _card_from_job(self, job: Job, company) -> JobCardOut:
        data = self._job_fields(job, exclude={"company_id", "created_by_admin_id"})
        data["company"] = JobCompanySummary.model_validate(company)
        data.update(self._derived(job))
        return JobCardOut.model_validate(data)

    def _admin_from_job(self, job: Job, company) -> JobAdminOut:
        data = self._job_fields(job, exclude={"company_id"})
        data.update(self._derived(job))
        data["company"] = CompanyOut.model_validate(company)
        data["is_saved"] = False
        return JobAdminOut.model_validate(data)

    async def to_card(self, job: Job) -> JobCardOut:
        company = await self._require_company(job.company_id)
        return self._card_from_job(job, company)

    async def to_detail(self, job: Job, *, saved_job_ids: set[str] | None = None) -> JobDetailOut:
        company = await self._require_company(job.company_id)
        data = self._job_fields(job, exclude={"company_id", "created_by_admin_id"})
        data["company"] = CompanyOut.model_validate(company)
        data["is_saved"] = job.id in saved_job_ids if saved_job_ids is not None else False
        data.update(self._derived(job))
        return JobDetailOut.model_validate(data)

    async def to_admin(self, job: Job) -> JobAdminOut:
        company = await self._require_company(job.company_id)
        return self._admin_from_job(job, company)

    async def _batch_companies(self, jobs: list[Job]) -> dict[str, object]:
        companies = await self.companies.get_by_ids({job.company_id for job in jobs})
        missing = {job.company_id for job in jobs} - companies.keys()
        if missing:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Job has no valid company")
        return companies

    async def list_public(self, *, viewer_user_id: str | None = None, **filters):
        items, total = await self.jobs.list_public(**filters)
        saved_ids = await self.jobs.list_saved_job_ids(viewer_user_id) if viewer_user_id else set()
        companies = await self._batch_companies(items)
        cards = [self._card_from_job(job, companies[job.company_id]) for job in items]
        for card in cards:
            card.is_saved = card.id in saved_ids
        return cards, total

    async def list_admin(self, *, page: int, page_size: int, search: str | None, job_status: str | None):
        items, total = await self.jobs.list_admin(
            page=page, page_size=page_size, search=search, status=job_status
        )
        companies = await self._batch_companies(items)
        return [self._admin_from_job(job, companies[job.company_id]) for job in items], total

    @staticmethod
    def _is_publicly_visible(job: Job) -> bool:
        """Listable/saveable: published, active at its source, not past deadline or expiry."""
        return publicly_listable(job)

    async def get_public(self, id_or_slug: str, *, viewer_user_id: str | None = None) -> JobDetailOut:
        """Detail stays reachable after a listing expires or leaves its source, so saved items and
        tracked applications keep working; `availability` tells the app not to offer Apply."""
        job = await self.jobs.get_by_id_or_slug(id_or_slug)
        if job is None or not publicly_viewable(job):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        saved_ids = await self.jobs.list_saved_job_ids(viewer_user_id) if viewer_user_id else set()
        return await self.to_detail(job, saved_job_ids=saved_ids)

    async def get_for_admin(self, job_id: str) -> Job:
        job = await self.jobs.get_by_id(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job

    async def create(self, payload: JobCreate, *, admin_id: str | None = None) -> JobAdminOut:
        company = await self.companies.get_by_id(payload.company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown company_id")

        slug = await self.jobs.generate_unique_slug(payload.title, company.name)
        job = Job(slug=slug, created_by_admin_id=admin_id, **payload.model_dump())
        self._apply_workflow_transitions(job, admin_id=admin_id)
        await self.jobs.create(job)
        await self.db.commit()
        await self.db.refresh(job)
        return await self.to_admin(job)

    async def update(self, job_id: str, payload: JobUpdate, *, admin_id: str | None = None) -> JobAdminOut:
        job = await self.get_for_admin(job_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(job, field, value)
        self._apply_workflow_transitions(job, admin_id=admin_id)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(job)
        return await self.to_admin(job)

    @staticmethod
    def _apply_workflow_transitions(job: Job, *, admin_id: str | None) -> None:
        """Spec §13 — track who reviewed/published, not just who created (spec §13's "Track:
        created_by, reviewed_by, published_by, timestamps")."""
        if job.status == ContentStatus.REVIEW and job.reviewed_by_admin_id is None:
            job.reviewed_by_admin_id = admin_id
        if job.status == ContentStatus.PUBLISHED:
            if job.published_at is None:
                job.published_at = datetime.now(timezone.utc)
            if job.published_by_admin_id is None:
                job.published_by_admin_id = admin_id

    async def delete(self, job_id: str) -> None:
        job = await self.get_for_admin(job_id)
        await self.jobs.delete(job)
        await self.db.commit()

    async def save_for_user(self, user_id: str, job_id: str) -> None:
        job = await self.jobs.get_by_id(job_id)
        if job is None or not self._is_publicly_visible(job):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        await self.jobs.save_job(user_id, job_id)
        await self.db.commit()

    async def unsave_for_user(self, user_id: str, job_id: str) -> None:
        await self.jobs.unsave_job(user_id, job_id)
        await self.db.commit()

    async def list_saved_for_user(self, user_id: str, *, page: int, page_size: int):
        items, total = await self.jobs.list_saved_jobs(user_id, page=page, page_size=page_size)
        cards = []
        for job in items:
            card = await self.to_card(job)
            card.is_saved = True
            cards.append(card)
        return cards, total
