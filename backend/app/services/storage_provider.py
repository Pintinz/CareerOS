import io
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB — generous for a source image, rejects abuse
MAX_DIMENSION_PX = 4096  # rejects absurd/decompression-bomb-style dimensions


@dataclass(frozen=True)
class StoredImage:
    url: str
    storage_key: str
    mime_type: str
    width: int
    height: int
    file_size: int


class StorageProvider(ABC):
    """Interface so a cloud provider (S3/Supabase Storage/etc.) can replace local disk storage
    later without touching callers — no cloud storage credentials are configured yet, so this
    ships with a local-disk implementation only (spec Rule 3). Shared by every feature that needs
    an image (jobs/companies/scholarships, and — as of Phase 7.5 — aptitude/interview question
    authoring) via the one admin upload endpoint, rather than a separate implementation per
    feature (spec §12)."""

    @abstractmethod
    async def save_image(self, file: UploadFile) -> str:
        """Validates and stores an image, returning a publicly servable URL."""

    @abstractmethod
    async def save_image_with_metadata(self, file: UploadFile) -> StoredImage:
        """Same validation/storage as `save_image`, but also returns real metadata (dimensions,
        MIME type, byte size) extracted from the decoded image — never trusted from client-
        supplied headers alone."""


class LocalStorageProvider(StorageProvider):
    def __init__(self, *, upload_dir: Path, public_base_url: str) -> None:
        self.upload_dir = upload_dir
        self.public_base_url = public_base_url.rstrip("/")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_image(self, file: UploadFile) -> str:
        stored = await self.save_image_with_metadata(file)
        return stored.url

    async def save_image_with_metadata(self, file: UploadFile) -> StoredImage:
        _validate_image_upload(file)

        suffix = Path(file.filename or "").suffix.lower() or _extension_for_content_type(file.content_type)
        # Randomized, non-guessable storage key — never derived from the client's filename, which
        # could otherwise smuggle path-traversal segments or collide with an existing file.
        storage_key = f"{uuid.uuid4()}{suffix}"
        destination = self.upload_dir / storage_key

        size = 0
        data = bytearray()
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
                )
            data.extend(chunk)

        # Decode with Pillow before writing anything to disk — this is the real content check:
        # a renamed executable or a corrupt file fails here regardless of what Content-Type or
        # extension the client claimed (spec §14/§31 — reject invalid/dangerous files).
        try:
            with Image.open(io.BytesIO(bytes(data))) as image:
                image.verify()
            with Image.open(io.BytesIO(bytes(data))) as image:
                width, height = image.size
                mime_type = Image.MIME.get(image.format or "", file.content_type or "application/octet-stream")
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is not a valid image."
            ) from exc

        if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Image dimensions exceed the {MAX_DIMENSION_PX}px limit.",
            )

        destination.write_bytes(bytes(data))

        return StoredImage(
            url=f"{self.public_base_url}/{storage_key}",
            storage_key=storage_key,
            mime_type=mime_type,
            width=width,
            height=height,
            file_size=size,
        )


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
