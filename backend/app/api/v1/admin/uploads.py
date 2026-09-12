from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import get_settings
from app.models.admin_user import AdminRole
from app.security.admin_dependencies import require_admin_role
from app.services.storage_provider import LocalStorageProvider

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)


def get_storage_provider() -> LocalStorageProvider:
    settings = get_settings()
    return LocalStorageProvider(
        upload_dir=Path(settings.upload_dir), public_base_url=f"{settings.public_base_url}/uploads"
    )


@router.post("/image", dependencies=[Depends(_CAN_WRITE)])
async def upload_image(file: UploadFile = File(...)) -> dict:
    url = await get_storage_provider().save_image(file)
    return {"url": url}
