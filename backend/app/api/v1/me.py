from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.company import CompanyOut
from app.schemas.job import JobListResponse
from app.schemas.scholarship import ScholarshipListResponse
from app.security.dependencies import get_current_user
from app.services.company_service import CompanyService
from app.services.job_service import JobService
from app.services.scholarship_service import ScholarshipService

router = APIRouter()


@router.get("/saved-jobs", response_model=JobListResponse)
async def list_saved_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobListResponse:
    items, total = await JobService(db).list_saved_for_user(user.id, page=page, page_size=page_size)
    return JobListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/saved-scholarships", response_model=ScholarshipListResponse)
async def list_saved_scholarships(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScholarshipListResponse:
    items, total = await ScholarshipService(db).list_saved_for_user(user.id, page=page, page_size=page_size)
    return ScholarshipListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/followed-companies", response_model=list[CompanyOut])
async def list_followed_companies(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CompanyOut]:
    return await CompanyService(db).list_followed(user.id)
