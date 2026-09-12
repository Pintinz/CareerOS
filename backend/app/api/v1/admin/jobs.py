from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.models.job import ContentStatus
from app.schemas.job import JobAdminListResponse, JobAdminOut, JobCreate, JobUpdate
from app.security.admin_dependencies import require_admin_role
from app.services.job_service import JobService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(
    AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER
)


@router.get("", response_model=JobAdminListResponse, dependencies=[Depends(_CAN_READ)])
async def list_jobs_admin(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    job_status: ContentStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> JobAdminListResponse:
    items, total = await JobService(db).list_admin(
        page=page, page_size=page_size, search=search, job_status=job_status
    )
    return JobAdminListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{job_id}", response_model=JobAdminOut, dependencies=[Depends(_CAN_READ)])
async def get_job_admin(job_id: str, db: AsyncSession = Depends(get_db)) -> JobAdminOut:
    service = JobService(db)
    job = await service.get_for_admin(job_id)
    return await service.to_admin(job)


@router.post(
    "", response_model=JobAdminOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_CAN_WRITE)]
)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)) -> JobAdminOut:
    return await JobService(db).create(payload)


@router.put("/{job_id}", response_model=JobAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def update_job(job_id: str, payload: JobUpdate, db: AsyncSession = Depends(get_db)) -> JobAdminOut:
    return await JobService(db).update(job_id, payload)


@router.post("/{job_id}/duplicate", response_model=JobAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def duplicate_job(job_id: str, db: AsyncSession = Depends(get_db)) -> JobAdminOut:
    service = JobService(db)
    original = await service.get_for_admin(job_id)
    duplicate_payload = JobCreate(
        **{
            field: getattr(original, field)
            for field in JobCreate.model_fields
            if hasattr(original, field)
        }
    )
    duplicate_payload.title = f"{original.title} (Copy)"
    duplicate_payload.status = ContentStatus.DRAFT
    return await service.create(duplicate_payload)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)) -> None:
    await JobService(db).delete(job_id)
