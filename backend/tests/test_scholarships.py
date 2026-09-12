import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_admin(db_session: AsyncSession) -> None:
    repo = AdminUserRepository(db_session)
    await repo.create(email="admin@example.com", hashed_password=hash_password("adminpass1"), role=AdminRole.ADMIN)
    await db_session.commit()


async def _admin_headers(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "admin@example.com", "password": "adminpass1"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _user_headers(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/register", json={"email": "student@example.com", "password": "studentpass1"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _scholarship_payload(**overrides) -> dict:
    payload = {
        "name": "Chevening Scholarship",
        "organization": "UK Government",
        "country": "United Kingdom",
        "degree_levels": ["MASTERS"],
        "funding_type": "FULLY_FUNDED",
        "official_url": "https://www.chevening.org/apply",
    }
    payload.update(overrides)
    return payload


async def test_full_scholarship_acceptance_workflow(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)

    create_response = await client.post(
        "/api/v1/admin/scholarships", headers=admin_headers, json=_scholarship_payload()
    )
    assert create_response.status_code == 201
    scholarship = create_response.json()
    assert scholarship["status"] == "DRAFT"
    scholarship_id = scholarship["id"]

    # Draft hidden from public feed.
    public_list = await client.get("/api/v1/scholarships")
    assert public_list.json()["total"] == 0

    publish_response = await client.put(
        f"/api/v1/admin/scholarships/{scholarship_id}", headers=admin_headers, json={"status": "PUBLISHED"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["published_at"] is not None

    public_list = await client.get("/api/v1/scholarships")
    body = public_list.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Chevening Scholarship"

    public_detail = await client.get(f"/api/v1/scholarships/{scholarship_id}")
    assert public_detail.status_code == 200
    assert public_detail.json()["official_url"] == "https://www.chevening.org/apply"

    user_headers = await _user_headers(client)
    save_response = await client.post(f"/api/v1/scholarships/{scholarship_id}/save", headers=user_headers)
    assert save_response.status_code == 204

    saved_list = await client.get("/api/v1/me/saved-scholarships", headers=user_headers)
    assert saved_list.json()["total"] == 1

    unsave_response = await client.delete(
        f"/api/v1/scholarships/{scholarship_id}/save", headers=user_headers
    )
    assert unsave_response.status_code == 204
    saved_list_after = await client.get("/api/v1/me/saved-scholarships", headers=user_headers)
    assert saved_list_after.json()["total"] == 0


async def test_scholarship_filters(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)

    fully_funded = await client.post(
        "/api/v1/admin/scholarships",
        headers=admin_headers,
        json=_scholarship_payload(name="Fully Funded PhD", funding_type="FULLY_FUNDED", degree_levels=["PHD"]),
    )
    partial = await client.post(
        "/api/v1/admin/scholarships",
        headers=admin_headers,
        json=_scholarship_payload(
            name="Partial Masters", funding_type="PARTIAL", degree_levels=["MASTERS"], country="Canada"
        ),
    )
    for resp in (fully_funded, partial):
        sid = resp.json()["id"]
        await client.put(
            f"/api/v1/admin/scholarships/{sid}", headers=admin_headers, json={"status": "PUBLISHED"}
        )

    funded_only = await client.get("/api/v1/scholarships", params={"funding_type": "FULLY_FUNDED"})
    assert funded_only.json()["total"] == 1
    assert funded_only.json()["items"][0]["name"] == "Fully Funded PhD"

    phd_only = await client.get("/api/v1/scholarships", params={"degree_level": "PHD"})
    assert phd_only.json()["total"] == 1

    canada_only = await client.get("/api/v1/scholarships", params={"country": "Canada"})
    assert canada_only.json()["total"] == 1
    assert canada_only.json()["items"][0]["name"] == "Partial Masters"


async def test_reviewer_cannot_create_scholarship(client: AsyncClient, db_session: AsyncSession) -> None:
    repo = AdminUserRepository(db_session)
    await repo.create(
        email="reviewer@example.com", hashed_password=hash_password("adminpass1"), role=AdminRole.REVIEWER
    )
    await db_session.commit()
    login = await client.post(
        "/api/v1/admin/auth/login", json={"email": "reviewer@example.com", "password": "adminpass1"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post("/api/v1/admin/scholarships", headers=headers, json=_scholarship_payload())
    assert response.status_code == 403


async def test_expired_scholarship_hidden_from_public(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    create_response = await client.post(
        "/api/v1/admin/scholarships", headers=admin_headers, json=_scholarship_payload()
    )
    sid = create_response.json()["id"]
    await client.put(f"/api/v1/admin/scholarships/{sid}", headers=admin_headers, json={"status": "PUBLISHED"})
    await client.put(f"/api/v1/admin/scholarships/{sid}", headers=admin_headers, json={"is_active": False})

    public_detail = await client.get(f"/api/v1/scholarships/{sid}")
    assert public_detail.status_code == 404
