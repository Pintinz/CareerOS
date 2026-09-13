import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio

# A genuinely valid 2x2 PNG (Pillow-encoded, so its IDAT checksum is actually correct) — the
# storage provider now decodes every upload with Pillow (spec §14/§31), so a fixture with a
# well-formed header but a broken chunk checksum would rightly be rejected as not a real image.
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd49a730000001049444154789c"
    "63fccf00024c609201000d1d010382c971ff0000000049454e44ae426082"
)


async def _admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    repo = AdminUserRepository(db_session)
    await repo.create(email="admin@example.com", hashed_password=hash_password("adminpass1"), role=AdminRole.ADMIN)
    await db_session.commit()
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "admin@example.com", "password": "adminpass1"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_upload_requires_admin_auth(client: AsyncClient) -> None:
    files = {"file": ("test.png", io.BytesIO(_TINY_PNG), "image/png")}
    response = await client.post("/api/v1/admin/uploads/image", files=files)
    assert response.status_code == 401


async def test_upload_valid_png(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _admin_headers(client, db_session)
    files = {"file": ("test.png", io.BytesIO(_TINY_PNG), "image/png")}
    response = await client.post("/api/v1/admin/uploads/image", headers=headers, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["url"].startswith("http://localhost:8000/uploads/")
    assert body["url"].endswith(".png")


async def test_upload_rejects_disallowed_content_type(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _admin_headers(client, db_session)
    files = {"file": ("script.js", io.BytesIO(b"alert(1)"), "application/javascript")}
    response = await client.post("/api/v1/admin/uploads/image", headers=headers, files=files)
    assert response.status_code == 422


async def test_media_library_lists_uploads_and_deletes_unreferenced_asset(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _admin_headers(client, db_session)
    files = {"file": ("test.png", io.BytesIO(_TINY_PNG), "image/png")}
    upload = await client.post("/api/v1/admin/uploads/image", headers=headers, files=files)
    asset_id = upload.json()["media_asset_id"]

    listing = await client.get("/api/v1/admin/uploads", headers=headers)
    assert listing.status_code == 200
    assert any(item["id"] == asset_id for item in listing.json())

    delete = await client.delete(f"/api/v1/admin/uploads/{asset_id}", headers=headers)
    assert delete.status_code == 204

    listing_after = await client.get("/api/v1/admin/uploads", headers=headers)
    assert all(item["id"] != asset_id for item in listing_after.json())


async def test_media_library_prevents_deleting_a_referenced_asset(client: AsyncClient, db_session: AsyncSession) -> None:
    from tests.test_jobs import _create_company, _job_payload

    headers = await _admin_headers(client, db_session)
    files = {"file": ("test.png", io.BytesIO(_TINY_PNG), "image/png")}
    upload = await client.post("/api/v1/admin/uploads/image", headers=headers, files=files)
    asset_id = upload.json()["media_asset_id"]
    thumbnail_url = upload.json()["url"]

    company_id = await _create_company(client, headers)
    await client.post("/api/v1/admin/jobs", headers=headers, json=_job_payload(company_id, thumbnail_url=thumbnail_url))

    delete = await client.delete(f"/api/v1/admin/uploads/{asset_id}", headers=headers)
    assert delete.status_code == 409
