from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.models.media import MediaAsset
from app.security.admin_dependencies import require_admin_role
from app.services import audit_service
from app.services.storage_provider import LocalStorageProvider

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER)

# Every column across content tables that can hold a media URL — checked before allowing a delete
# (spec §23: "If asset is referenced by published content: prevent unsafe deletion"). This is a
# text-search approximation, not a real usage-reference join table (no such table exists yet — see
# ARCHITECTURE.md) but it is a genuine, real check against live content, not a no-op.
_URL_COLUMNS = [
    ("jobs", ["thumbnail_url", "post_image_url"]),
    ("companies", ["logo_url", "banner_url"]),
    ("scholarships", ["thumbnail_url", "post_image_url"]),
    ("intelligence_posts", ["thumbnail_url", "post_image_url"]),
    ("questions", ["question_image_url"]),
    ("question_options", ["option_image_url"]),
]


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


@router.get("", dependencies=[Depends(_CAN_READ)])
async def list_media_admin(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(MediaAsset).order_by(MediaAsset.created_at.desc()))
    return [
        {
            "id": a.id, "storage_key": a.storage_key, "url": a.url, "mime_type": a.mime_type,
            "width": a.width, "height": a.height, "file_size": a.file_size, "alt_text": a.alt_text,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


async def _is_referenced(db: AsyncSession, url: str) -> bool:
    for table, columns in _URL_COLUMNS:
        conditions = " OR ".join(f"{col} = :url" for col in columns)
        result = await db.execute(text(f"SELECT 1 FROM {table} WHERE {conditions} LIMIT 1"), {"url": url})  # noqa: S608 — table/column names come from the fixed _URL_COLUMNS constant above, never user input.
        if result.first() is not None:
            return True
    return False


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(_CAN_WRITE)])
async def delete_media_admin(asset_id: str, db: AsyncSession = Depends(get_db), admin=Depends(_CAN_WRITE)) -> None:
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    if await _is_referenced(db, asset.url):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This asset is referenced by existing content — replace it there first before deleting.",
        )
    storage_path = Path(get_settings().upload_dir) / asset.storage_key
    if storage_path.exists():
        storage_path.unlink()
    await db.delete(asset)
    await db.commit()
    await audit_service.record(db, admin_id=admin.id, action="delete", entity_type="media_asset", entity_id=asset_id)
