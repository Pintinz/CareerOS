import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB — generous for a source image, rejects abuse


class StorageProvider(ABC):
    """Interface so a cloud provider (S3/Supabase Storage/etc.) can replace local disk storage
    later without touching callers — no cloud storage credentials are configured yet, so this
    ships with a local-disk implementation only (spec Rule 3)."""

    @abstractmethod
    async def save_image(self, file: UploadFile) -> str:
        """Validates and stores an image, returning a publicly servable URL."""


class LocalStorageProvider(StorageProvider):
    def __init__(self, *, upload_dir: Path, public_base_url: str) -> None:
        self.upload_dir = upload_dir
        self.public_base_url = public_base_url.rstrip("/")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_image(self, file: UploadFile) -> str:
        _validate_image_upload(file)

        suffix = Path(file.filename or "").suffix.lower() or _extension_for_content_type(file.content_type)
        filename = f"{uuid.uuid4()}{suffix}"
        destination = self.upload_dir / filename

        size = 0
        with destination.open("wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    out_file.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Image exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
                    )
                out_file.write(chunk)

        return f"{self.public_base_url}/{filename}"


def _validate_image_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported image type '{file.content_type}'. Allowed: JPG, JPEG, PNG, WEBP.",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file extension '{suffix}'. Allowed: .jpg, .jpeg, .png, .webp.",
        )


def _extension_for_content_type(content_type: str | None) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(content_type or "", ".jpg")
