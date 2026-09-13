from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.schemas.admin_ops import SettingOut, SettingUpdate
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service, system_settings_service

router = APIRouter()

# Spec §35: "Only SUPER_ADMIN where appropriate" — system settings affect scoring/matching/
# classification behavior platform-wide, so both read and write are SUPER_ADMIN-only here.
_SUPER_ADMIN_ONLY = require_admin_role(AdminRole.SUPER_ADMIN)


@router.get("", response_model=dict[str, SettingOut], dependencies=[Depends(_SUPER_ADMIN_ONLY)])
async def list_settings(db: AsyncSession = Depends(get_db)) -> dict[str, SettingOut]:
    settings = await system_settings_service.get_all(db)
    return {key: SettingOut(key=key, **value) for key, value in settings.items()}


@router.put("/{key}", response_model=SettingOut, dependencies=[Depends(_SUPER_ADMIN_ONLY)])
async def update_setting(
    key: str, payload: SettingUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(_SUPER_ADMIN_ONLY)
) -> SettingOut:
    try:
        await system_settings_service.set_value(db, key, payload.value, admin_id=admin.id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown setting key")
    await audit_service.record(db, admin_id=admin.id, action="update_setting", entity_type="system_setting", entity_id=key)
    all_settings = await system_settings_service.get_all(db)
    return SettingOut(key=key, **all_settings[key])
