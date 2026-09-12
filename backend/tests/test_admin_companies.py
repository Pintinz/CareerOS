import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_admin(
    db_session: AsyncSession, *, email: str = "admin@example.com", password: str = "adminpass1", role=AdminRole.ADMIN
):
    repo = AdminUserRepository(db_session)
    admin = await repo.create(email=email, hashed_password=hash_password(password), role=role)
    await db_session.commit()
    return admin


async def _admin_login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post("/api/v1/admin/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_admin_login_rejects_bad_password(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "admin@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


async def test_admin_token_cannot_access_consumer_me(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_token = await _admin_login(client, "admin@example.com", "adminpass1")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 401


async def test_consumer_token_cannot_access_admin_routes(client: AsyncClient) -> None:
    register = await client.post(
        "/api/v1/auth/register", json={"email": "user@example.com", "password": "userpass1"}
    )
    user_token = register.json()["access_token"]
    response = await client.get(
        "/api/v1/admin/companies", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 401


async def test_admin_can_create_and_publish_company(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    token = await _admin_login(client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/admin/companies",
        headers=headers,
        json={"name": "ExxonMobil", "country": "Nigeria", "industry": "Energy"},
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["slug"] == "exxonmobil"
    assert body["is_active"] is True


async def test_reviewer_cannot_create_company(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session, email="reviewer@example.com", role=AdminRole.REVIEWER)
    token = await _admin_login(client, "reviewer@example.com", "adminpass1")
    response = await client.post(
        "/api/v1/admin/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Shell"},
    )
    assert response.status_code == 403


async def test_public_only_sees_active_companies(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    token = await _admin_login(client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    active = await client.post(
        "/api/v1/admin/companies", headers=headers, json={"name": "Active Co"}
    )
    inactive = await client.post(
        "/api/v1/admin/companies", headers=headers, json={"name": "Inactive Co", "is_active": False}
    )
    assert active.status_code == 201
    assert inactive.status_code == 201

    public_list = await client.get("/api/v1/companies")
    names = [c["name"] for c in public_list.json()["items"]]
    assert "Active Co" in names
    assert "Inactive Co" not in names

    inactive_id = inactive.json()["id"]
    public_detail = await client.get(f"/api/v1/companies/{inactive_id}")
    assert public_detail.status_code == 404


async def test_company_search_and_pagination(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    token = await _admin_login(client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    for name in ["Shell Nigeria", "Chevron", "Shell Global"]:
        resp = await client.post("/api/v1/admin/companies", headers=headers, json={"name": name})
        assert resp.status_code == 201

    search_response = await client.get("/api/v1/companies", params={"search": "shell"})
    body = search_response.json()
    assert body["total"] == 2
    assert all("shell" in c["name"].lower() for c in body["items"])


async def test_admin_update_and_delete_company(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    token = await _admin_login(client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/admin/companies", headers=headers, json={"name": "Test Co"}
    )
    company_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/admin/companies/{company_id}", headers=headers, json={"is_verified": True}
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_verified"] is True

    delete_response = await client.delete(f"/api/v1/admin/companies/{company_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/admin/companies/{company_id}", headers=headers)
    assert get_response.status_code == 404
