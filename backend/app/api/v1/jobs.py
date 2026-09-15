from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job import EmploymentType, ExperienceLevel, OpportunityType, WorkMode
from app.models.user import User
from app.schemas.job import JobDetailOut, JobListResponse
from app.security.dependencies import get_current_user, get_optional_current_user
from app.services.job_service import JobService

router = APIRouter()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    # A country name or a region such as "Africa".
    country: str | None = None,
    location: str | None = None,
    industry: str | None = None,
    employment_type: EmploymentType | None = None,
    work_mode: WorkMode | None = None,
    experience_level: ExperienceLevel | None = None,
    is_featured: bool | None = None,
    company_id: str | None = None,
    opportunity_type: OpportunityType | None = None,
    posted_within_days: int | None = Query(default=None, ge=1, le=365),
    job_function: str | None = Query(default=None, max_length=100),
    sort: str = Query(default="newest", pattern="^(newest|recommended|deadline)$"),
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_current_user),
) -> JobListResponse:
    items, total = await JobService(db).list_public(
        viewer_user_id=viewer.id if viewer else None,
        page=page,
        page_size=page_size,
        search=search,
        country=country,
        location=location,
        industry=industry,
        employment_type=employment_type,
        work_mode=work_mode,
        experience_level=experience_level,
        is_featured=is_featured,
        company_id=company_id,
        opportunity_type=opportunity_type,
        posted_within_days=posted_within_days,
        job_function=job_function,
        sort=sort,
    )
    return JobListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{id_or_slug}", response_model=JobDetailOut)
async def get_job(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_current_user),
) -> JobDetailOut:
    return await JobService(db).get_public(id_or_slug, viewer_user_id=viewer.id if viewer else None)


@router.post("/{job_id}/save", status_code=status.HTTP_204_NO_CONTENT)
async def save_job(
    job_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await JobService(db).save_for_user(user.id, job_id)


@router.delete("/{job_id}/save", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_job(
    job_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await JobService(db).unsave_for_user(user.id, job_id)
