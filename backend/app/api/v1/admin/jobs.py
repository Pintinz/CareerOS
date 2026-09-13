from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.models.job import ContentStatus
from app.schemas.job import JobAdminListResponse, JobAdminOut, JobCreate, JobUpdate
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
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
async def create_job(
    payload: JobCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> JobAdminOut:
    job = await JobService(db).create(payload, admin_id=admin.id)
    await audit_service.record(db, admin_id=admin.id, action="create", entity_type="job", entity_id=job.id)
    return job


@router.put("/{job_id}", response_model=JobAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def update_job(
    job_id: str, payload: JobUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> JobAdminOut:
    job = await JobService(db).update(job_id, payload, admin_id=admin.id)
    action = "publish" if payload.status == ContentStatus.PUBLISHED else "update"
    await audit_service.record(db, admin_id=admin.id, action=action, entity_type="job", entity_id=job_id)
    return job


@router.post("/{job_id}/duplicate", response_model=JobAdminOut, dependencies=[Depends(_CAN_WRITE)])
async def duplicate_job(
    job_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> JobAdminOut:
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
    duplicate_payload.scheduled_publish_at = None
    job = await service.create(duplicate_payload, admin_id=admin.id)
    await audit_service.record(
        db, admin_id=admin.id, action="duplicate", entity_type="job", entity_id=job.id, metadata={"source_job_id": job_id}
    )
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_job(
    job_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))
) -> None:
    await JobService(db).delete(job_id)
    await audit_service.record(db, admin_id=admin.id, action="delete", entity_type="job", entity_id=job_id)
