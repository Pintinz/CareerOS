from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_ops import DiscoveryRunTrigger
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.admin_ops import (
    ContentSourceCreate,
    ContentSourceOut,
    ContentSourceUpdate,
    DiscoveryRunOut,
    SeedImportOut,
    SourceHealthOut,
    SourceTestOut,
)
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
from app.services.discovery.review import ContentSourceService
from app.services.discovery.source_seed import import_career_sources, load_seed
from app.services.discovery.worker import DiscoveryTaskRunner, enqueue_source_run, get_discovery_task_runner

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)
_CAN_MANAGE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN)

# Trust decisions change what may be verified or auto-published, so only admins make them.
_TRUST_FIELDS = {"trust_level", "auto_publish_allowed", "verification_status"}


@router.get("", response_model=list[SourceHealthOut], dependencies=[Depends(_CAN_READ)])
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[SourceHealthOut]:
    """Every registered source with its health: last check/success/failure, item counts, last run."""
    return await ContentSourceService(db).health()


class SeedImportIn(BaseModel):
    dry_run: bool = False


@router.post("/import-seed", response_model=SeedImportOut)
async def import_seed(payload: SeedImportIn, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_MANAGE)) -> SeedImportOut:
    """Applies the bundled career-source pack (idempotent; never overrides admins' operational choices)."""
    result = await import_career_sources(db, load_seed(), admin_id=admin.id, dry_run=payload.dry_run)
    if not payload.dry_run:
        await audit_service.record(
            db, admin_id=admin.id, action="career_sources_imported", entity_type="content_source", entity_id=None,
            metadata={"created": result.sources_created, "updated": result.sources_updated, "companies_created": result.companies_created},
        )
    return SeedImportOut(**result.__dict__)


@router.post("/{source_id}/test", response_model=SourceTestOut)
async def test_source(source_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)) -> SourceTestOut:
    """Test connection: a bounded live fetch (at most 15 requests, 5 listings) through the source's
    adapter. Nothing is stored; use Run discovery to sync."""
    outcome = await ContentSourceService(db).test_connection(source_id)
    await audit_service.record(
        db, admin_id=admin.id, action="source_tested", entity_type="content_source", entity_id=source_id,
        metadata={"ok": outcome.ok, "found": outcome.found, "error_code": outcome.error_code},
    )
    return outcome


@router.get("/{source_id}", response_model=ContentSourceOut, dependencies=[Depends(_CAN_READ)])
async def get_source(source_id: str, db: AsyncSession = Depends(get_db)) -> ContentSourceOut:
    return ContentSourceOut.model_validate(await ContentSourceService(db).get_or_404(source_id))


@router.post("", response_model=ContentSourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: ContentSourceCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> ContentSourceOut:
    if admin.role not in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN) and (payload.auto_publish_allowed or payload.trust_level):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can set trust level or allow auto-publishing.")
    source = await ContentSourceService(db).create(payload, admin_id=admin.id)
    await audit_service.record(
        db, admin_id=admin.id, action="source_created", entity_type="content_source", entity_id=source.id,
        metadata={"source_type": source.source_type.value, "domain": source.domain},
    )
    return ContentSourceOut.model_validate(source)


@router.put("/{source_id}", response_model=ContentSourceOut)
async def update_source(
    source_id: str, payload: ContentSourceUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> ContentSourceOut:
    if admin.role not in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN) and _TRUST_FIELDS & payload.model_dump(exclude_unset=True).keys():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change trust level, verification or auto-publishing.")
    source, fields = await ContentSourceService(db).update(source_id, payload)
    await audit_service.record(db, admin_id=admin.id, action="source_edited", entity_type="content_source", entity_id=source_id, metadata={"fields": fields})
    return ContentSourceOut.model_validate(source)


@router.post("/{source_id}/pause", response_model=ContentSourceOut)
async def pause_source(source_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)) -> ContentSourceOut:
    service = ContentSourceService(db)
    source = await service.get_or_404(source_id)
    source.is_active = False
    await db.commit()
    await audit_service.record(db, admin_id=admin.id, action="source_paused", entity_type="content_source", entity_id=source_id)
    return ContentSourceOut.model_validate(source)


@router.post("/{source_id}/resume", response_model=ContentSourceOut)
async def resume_source(source_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)) -> ContentSourceOut:
    service = ContentSourceService(db)
    source = await service.get_or_404(source_id)
    source.is_active = True
    source.next_poll_after = None
    await db.commit()
    await audit_service.record(db, admin_id=admin.id, action="source_resumed", entity_type="content_source", entity_id=source_id)
    return ContentSourceOut.model_validate(source)


@router.post("/{source_id}/run", response_model=DiscoveryRunOut, status_code=status.HTTP_202_ACCEPTED)
async def run_source_discovery(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(_CAN_WRITE),
    runner: DiscoveryTaskRunner = Depends(get_discovery_task_runner),
) -> DiscoveryRunOut:
    """Enqueues discovery and returns immediately (202). Poll GET /{source_id}/runs for the outcome."""
    source = await ContentSourceService(db).get_or_404(source_id)
    if not source.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resume this source before running discovery.")
    run, created = await enqueue_source_run(db, source, trigger=DiscoveryRunTrigger.MANUAL, admin_id=admin.id)
    if created:
        runner.enqueue(run.id)
        await audit_service.record(db, admin_id=admin.id, action="discovery_run_requested", entity_type="content_source", entity_id=source_id, metadata={"run_id": run.id})
    return DiscoveryRunOut.model_validate(run)


@router.get("/{source_id}/runs", response_model=list[DiscoveryRunOut], dependencies=[Depends(_CAN_READ)])
async def list_source_runs(source_id: str, limit: int = Query(default=20, ge=1, le=100), db: AsyncSession = Depends(get_db)) -> list[DiscoveryRunOut]:
    return [DiscoveryRunOut.model_validate(r) for r in await ContentSourceService(db).runs(source_id, limit=limit)]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_MANAGE)) -> None:
    await ContentSourceService(db).delete(source_id)
    await audit_service.record(db, admin_id=admin.id, action="source_deleted", entity_type="content_source", entity_id=source_id)
