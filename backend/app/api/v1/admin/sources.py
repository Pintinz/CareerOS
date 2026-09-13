from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.admin_ops import ContentSourceCreate, ContentSourceOut, ContentSourceUpdate
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
from app.services.admin_ops_service import ContentSourceService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)


@router.get("", response_model=list[ContentSourceOut], dependencies=[Depends(_CAN_READ)])
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[ContentSourceOut]:
    sources = await ContentSourceService(db).list_all()
    return [ContentSourceOut.model_validate(s) for s in sources]


@router.get("/{source_id}", response_model=ContentSourceOut, dependencies=[Depends(_CAN_READ)])
async def get_source(source_id: str, db: AsyncSession = Depends(get_db)) -> ContentSourceOut:
    source = await ContentSourceService(db).get_or_404(source_id)
    return ContentSourceOut.model_validate(source)


@router.post("", response_model=ContentSourceOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_CAN_WRITE)])
async def create_source(
    payload: ContentSourceCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> ContentSourceOut:
    source = await ContentSourceService(db).create(payload, admin_id=admin.id)
    await audit_service.record(db, admin_id=admin.id, action="create", entity_type="content_source", entity_id=source.id)
    return ContentSourceOut.model_validate(source)


@router.put("/{source_id}", response_model=ContentSourceOut, dependencies=[Depends(_CAN_WRITE)])
async def update_source(
    source_id: str, payload: ContentSourceUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_CAN_WRITE)
) -> ContentSourceOut:
    source = await ContentSourceService(db).update(source_id, payload)
    await audit_service.record(db, admin_id=admin.id, action="update", entity_type="content_source", entity_id=source_id)
    return ContentSourceOut.model_validate(source)


@router.delete(
    "/{source_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_source(
    source_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))
) -> None:
    await ContentSourceService(db).delete(source_id)
    await audit_service.record(db, admin_id=admin.id, action="delete", entity_type="content_source", entity_id=source_id)
