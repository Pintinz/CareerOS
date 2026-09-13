from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.models.media import MediaAsset
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
async def upload_image(
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Shared image upload used by every admin authoring flow that needs one — jobs/companies/
    scholarships, and (Phase 7.5) aptitude/interview question images. Every upload is recorded as
    a `MediaAsset` for provenance/reuse tracking (spec §12-13); the response still returns a plain
    `url` first so existing callers that only ever read that field keep working unchanged."""
    stored = await get_storage_provider().save_image_with_metadata(file)
    asset = MediaAsset(
        storage_key=stored.storage_key,
        url=stored.url,
        mime_type=stored.mime_type,
        width=stored.width,
        height=stored.height,
        file_size=stored.file_size,
        alt_text=alt_text,
    )
    db.add(asset)
    await db.commit()
    return {
        "url": stored.url,
        "media_asset_id": asset.id,
        "alt_text": alt_text,
        "width": stored.width,
        "height": stored.height,
        "mime_type": stored.mime_type,
        "file_size": stored.file_size,
    }
