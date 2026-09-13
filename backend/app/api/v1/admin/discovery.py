from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_ops import DiscoveredItemStatus, DiscoveredItemType
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.admin_ops import DiscoveredItemCreate, DiscoveredItemOut, DiscoveryDraftIn
from app.schemas.pagination import PaginatedResponse
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
from app.services.admin_ops_service import DiscoveryService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)


class DiscoveredItemListResponse(PaginatedResponse[DiscoveredItemOut]):
    pass


@router.get("", response_model=DiscoveredItemListResponse, dependencies=[Depends(_CAN_READ)])
async def list_discovery(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    item_type: DiscoveredItemType | None = None,
    item_status: DiscoveredItemStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> DiscoveredItemListResponse:
    items, total = await DiscoveryService(db).list_admin(item_type=item_type, item_status=item_status, page=page, page_size=page_size)
    return DiscoveredItemListResponse(
        items=[DiscoveredItemOut.model_validate(i) for i in items], page=page, page_size=page_size, total=total
    )


@router.get("/{item_id}", response_model=DiscoveredItemOut, dependencies=[Depends(_CAN_READ)])
async def get_discovery_item(item_id: str, db: AsyncSession = Depends(get_db)) -> DiscoveredItemOut:
    item = await DiscoveryService(db).get_or_404(item_id)
    return DiscoveredItemOut.model_validate(item)


@router.post("/ingest", response_model=DiscoveredItemOut | None, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_CAN_WRITE)])
async def ingest_discovery_item(payload: DiscoveredItemCreate, db: AsyncSession = Depends(get_db)) -> DiscoveredItemOut | None:
    """Manual entry point (spec §28's "Run Sync" concept, without a live adapter behind it yet —
    see ARCHITECTURE.md). Returns null when this is a duplicate of an already-tracked item."""
    item = await DiscoveryService(db).ingest(payload)
    return DiscoveredItemOut.model_validate(item) if item else None


@router.post("/{item_id}/ignore", response_model=DiscoveredItemOut, dependencies=[Depends(_CAN_WRITE)])
async def ignore_discovery_item(
    item_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> DiscoveredItemOut:
    item = await DiscoveryService(db).ignore(item_id, admin_id=admin.id)
    return DiscoveredItemOut.model_validate(item)


@router.post("/{item_id}/reject", response_model=DiscoveredItemOut, dependencies=[Depends(_CAN_WRITE)])
async def reject_discovery_item(
    item_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> DiscoveredItemOut:
    item = await DiscoveryService(db).reject(item_id, admin_id=admin.id)
    return DiscoveredItemOut.model_validate(item)


@router.post("/{item_id}/create-draft", dependencies=[Depends(_CAN_WRITE)])
async def create_draft_from_discovery(
    item_id: str, payload: DiscoveryDraftIn, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> dict:
    result = await DiscoveryService(db).create_draft(item_id, payload, admin_id=admin.id)
    await audit_service.record(
        db, admin_id=admin.id, action="create_draft", entity_type="discovered_item", entity_id=item_id, metadata=result
    )
    return result
