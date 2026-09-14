from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_ops import ChangeStatus, DiscoveredItemStatus, DiscoveredItemType, DiscoveryRun, DiscoveryRunStatus, DiscoveryRunTrigger
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.admin_ops import (
    CompanyProposalIn,
    ContentChangeOut,
    DiscoveredItemCreate,
    DiscoveredItemOut,
    DiscoveryDraftIn,
    DiscoveryMetricsOut,
    DiscoveryReviewOut,
    DiscoveryRunOut,
    SourceStateDecisionIn,
)
from app.schemas.company import CompanyOut
from app.schemas.pagination import PaginatedResponse
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
from app.services.discovery.records import ENTITY_INTELLIGENCE, ENTITY_JOB, ENTITY_SCHOLARSHIP
from app.services.discovery.review import DiscoveryService
from app.services.discovery.worker import DiscoveryTaskRunner, enqueue_due_sources, get_discovery_task_runner

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)
_ENTITY_TYPES = {ENTITY_JOB, ENTITY_SCHOLARSHIP, ENTITY_INTELLIGENCE}


class DiscoveredItemListResponse(PaginatedResponse[DiscoveredItemOut]):
    pass


@router.get("", response_model=DiscoveredItemListResponse, dependencies=[Depends(_CAN_READ)])
async def list_discovery(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    item_type: DiscoveredItemType | None = None,
    item_status: DiscoveredItemStatus | None = Query(default=None, alias="status"),
    source_id: str | None = None,
    company_id: str | None = None,
    country: str | None = Query(default=None, max_length=255),
    min_trust: int | None = Query(default=None, ge=1, le=5),
    duplicates: str | None = Query(default=None, pattern="^(only|exclude)$"),
    discovered_after: datetime | None = None,
    search: str | None = Query(default=None, max_length=200),
    db: AsyncSession = Depends(get_db),
) -> DiscoveredItemListResponse:
    """Defaults to the review queue (NEW / NEEDS_REVIEW / VERIFIED); pass `status` for other states."""
    items, total = await DiscoveryService(db).list_admin(
        page=page, page_size=page_size, item_type=item_type, item_status=item_status, source_id=source_id, company_id=company_id,
        country=country, min_trust=min_trust, duplicates=duplicates, discovered_after=discovered_after, search=search,
    )
    return DiscoveredItemListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/metrics", response_model=DiscoveryMetricsOut, dependencies=[Depends(_CAN_READ)])
async def discovery_metrics(db: AsyncSession = Depends(get_db)) -> DiscoveryMetricsOut:
    return await DiscoveryService(db).metrics()


@router.get("/runs", response_model=list[DiscoveryRunOut], dependencies=[Depends(_CAN_READ)])
async def recent_runs(limit: int = Query(default=30, ge=1, le=100), db: AsyncSession = Depends(get_db)) -> list[DiscoveryRunOut]:
    rows = (await db.execute(select(DiscoveryRun).order_by(DiscoveryRun.queued_at.desc()).limit(limit))).scalars().all()
    return [DiscoveryRunOut.model_validate(r) for r in rows]


@router.post("/run-due", status_code=status.HTTP_202_ACCEPTED)
async def run_due_sources(
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE), runner: DiscoveryTaskRunner = Depends(get_discovery_task_runner)
) -> dict:
    """Enqueue every polling source whose interval has elapsed (the same rule the scheduler uses)."""
    queued = await enqueue_due_sources(db)
    run_ids = (await db.execute(select(DiscoveryRun.id).where(DiscoveryRun.status == DiscoveryRunStatus.QUEUED))).scalars().all()
    for run_id in run_ids:
        runner.enqueue(run_id)
    await audit_service.record(db, admin_id=admin.id, action="discovery_run_requested", entity_type="discovery", metadata={"queued": queued})
    return {"queued": queued}


@router.post("/verify", status_code=status.HTTP_202_ACCEPTED)
async def run_verification(
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE), runner: DiscoveryTaskRunner = Depends(get_discovery_task_runner)
) -> dict:
    runner.enqueue_verification(DiscoveryRunTrigger.MANUAL)
    await audit_service.record(db, admin_id=admin.id, action="verification_run_requested", entity_type="discovery")
    return {"queued": True}


@router.get("/changes", response_model=list[ContentChangeOut], dependencies=[Depends(_CAN_READ)])
async def list_changes(
    entity_type: str | None = Query(default=None, pattern="^(JOB|SCHOLARSHIP|INTELLIGENCE)$"),
    entity_id: str | None = None,
    change_status: ChangeStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ContentChangeOut]:
    return await DiscoveryService(db).changes(entity_type=entity_type, entity_id=entity_id, change_status=change_status, limit=limit)


@router.post("/changes/{change_id}/apply", response_model=ContentChangeOut)
async def apply_change(change_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)) -> ContentChangeOut:
    return await DiscoveryService(db).decide_change(change_id, apply=True, admin_id=admin.id)


@router.post("/changes/{change_id}/dismiss", response_model=ContentChangeOut)
async def dismiss_change(change_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)) -> ContentChangeOut:
    return await DiscoveryService(db).decide_change(change_id, apply=False, admin_id=admin.id)


@router.post("/records/{entity_type}/{entity_id}/source-state")
async def decide_source_state(
    entity_type: str, entity_id: str, payload: SourceStateDecisionIn, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> dict:
    """Confirm a detected removal/closure (the record expires but is kept) or mark it still active."""
    if entity_type.upper() not in _ENTITY_TYPES - {ENTITY_INTELLIGENCE}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="entity_type must be JOB or SCHOLARSHIP")
    return await DiscoveryService(db).decide_source_state(entity_type.upper(), entity_id, confirm=payload.confirm, admin_id=admin.id)


@router.post("/ingest", response_model=DiscoveredItemOut | None, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_CAN_WRITE)])
async def ingest_discovery_item(payload: DiscoveredItemCreate, db: AsyncSession = Depends(get_db)) -> DiscoveredItemOut | None:
    """Manual report of something an editor spotted. Returns null for an already-tracked item."""
    service = DiscoveryService(db)
    item = await service.ingest(payload)
    return (await service.to_out([item]))[0] if item else None


@router.get("/{item_id}", response_model=DiscoveredItemOut, dependencies=[Depends(_CAN_READ)])
async def get_discovery_item(item_id: str, db: AsyncSession = Depends(get_db)) -> DiscoveredItemOut:
    service = DiscoveryService(db)
    return (await service.to_out([await service.get_or_404(item_id)]))[0]


@router.get("/{item_id}/review", response_model=DiscoveryReviewOut, dependencies=[Depends(_CAN_READ)])
async def review_discovery_item(item_id: str, db: AsyncSession = Depends(get_db)) -> DiscoveryReviewOut:
    return await DiscoveryService(db).review(item_id)


@router.post("/{item_id}/ignore", response_model=DiscoveredItemOut)
async def ignore_discovery_item(item_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)) -> DiscoveredItemOut:
    service = DiscoveryService(db)
    item = await service.ignore(item_id, admin_id=admin.id)
    await audit_service.record(db, admin_id=admin.id, action="discovery_ignored", entity_type="discovered_item", entity_id=item_id)
    return (await service.to_out([item]))[0]


@router.post("/{item_id}/reject", response_model=DiscoveredItemOut)
async def reject_discovery_item(item_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)) -> DiscoveredItemOut:
    service = DiscoveryService(db)
    item = await service.reject(item_id, admin_id=admin.id)
    await audit_service.record(db, admin_id=admin.id, action="discovery_rejected", entity_type="discovered_item", entity_id=item_id)
    return (await service.to_out([item]))[0]


@router.post("/{item_id}/create-draft")
async def create_draft_from_discovery(
    item_id: str, payload: DiscoveryDraftIn, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> dict:
    """Creates a DRAFT record from the reviewed item. Audited as `discovery_draft_created`."""
    return await DiscoveryService(db).create_draft(item_id, payload, admin_id=admin.id)


@router.post("/{item_id}/publish")
async def publish_discovery_item(
    item_id: str, payload: DiscoveryDraftIn, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> dict:
    """Publishes the reviewed item (or its existing draft). Audited as `discovery_published`."""
    return await DiscoveryService(db).publish(item_id, payload, admin_id=admin.id)


@router.post("/{item_id}/create-company", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def create_company_from_discovery(
    item_id: str, payload: CompanyProposalIn, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> CompanyOut:
    company = await DiscoveryService(db).create_company(item_id, payload, admin_id=admin.id)
    return CompanyOut.model_validate(company)
