from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_admin(db_session: AsyncSession, role=AdminRole.ADMIN) -> None:
    repo = AdminUserRepository(db_session)
    await repo.create(email="admin@example.com", hashed_password=hash_password("adminpass1"), role=role)
    await db_session.commit()


async def _admin_headers(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "admin@example.com", "password": "adminpass1"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _user_headers(client: AsyncClient, email: str = "candidate@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "candidatepass1"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_company(client: AsyncClient, headers: dict, name: str = "ExxonMobil") -> str:
    response = await client.post("/api/v1/admin/companies", headers=headers, json={"name": name})
    return response.json()["id"]


def _job_payload(company_id: str, **overrides) -> dict:
    payload = {
        "company_id": company_id,
        "title": "Process Technician",
        "location": "Lagos, Nigeria",
        "country": "Nigeria",
        "employment_type": "FULL_TIME",
        "work_mode": "ON_SITE",
        "application_url": "https://careers.exxonmobil.com/apply/123",
        "thumbnail_url": "https://cdn.example.com/thumb.jpg",
    }
    payload.update(overrides)
    return payload


async def test_full_job_acceptance_workflow(client: AsyncClient, db_session: AsyncSession) -> None:
    """Admin creates company -> creates draft job -> draft hidden -> publishes -> mobile sees
    it -> user saves it -> saved job persists -> application_url is exposed for Apply."""
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)

    company_id = await _create_company(client, admin_headers)

    draft_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id)
    )
    assert draft_response.status_code == 201
    job = draft_response.json()
    assert job["status"] == "DRAFT"
    job_id = job["id"]

    # Draft must not appear in the public feed or be fetchable by slug/id publicly.
    public_list = await client.get("/api/v1/jobs")
    assert public_list.json()["total"] == 0
    public_detail = await client.get(f"/api/v1/jobs/{job_id}")
    assert public_detail.status_code == 404

    publish_response = await client.put(
        f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "PUBLISHED"

    # Now it appears publicly.
    public_list = await client.get("/api/v1/jobs")
    body = public_list.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Process Technician"
    assert body["items"][0]["company"]["name"] == "ExxonMobil"

    public_detail = await client.get(f"/api/v1/jobs/{job_id}")
    assert public_detail.status_code == 200
    detail = public_detail.json()
    assert detail["application_url"] == "https://careers.exxonmobil.com/apply/123"
    assert detail["is_saved"] is False

    # A logged-in user saves it.
    user_headers = await _user_headers(client)
    save_response = await client.post(f"/api/v1/jobs/{job_id}/save", headers=user_headers)
    assert save_response.status_code == 204

    saved_detail = await client.get(f"/api/v1/jobs/{job_id}", headers=user_headers)
    assert saved_detail.json()["is_saved"] is True

    saved_list = await client.get("/api/v1/me/saved-jobs", headers=user_headers)
    saved_body = saved_list.json()
    assert saved_body["total"] == 1
    assert saved_body["items"][0]["id"] == job_id

    unsave_response = await client.delete(f"/api/v1/jobs/{job_id}/save", headers=user_headers)
    assert unsave_response.status_code == 204
    saved_list_after = await client.get("/api/v1/me/saved-jobs", headers=user_headers)
    assert saved_list_after.json()["total"] == 0


async def test_reviewer_cannot_publish_job(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session, role=AdminRole.ADMIN)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    repo = AdminUserRepository(db_session)
    await repo.create(
        email="reviewer@example.com", hashed_password=hash_password("adminpass1"), role=AdminRole.REVIEWER
    )
    await db_session.commit()
    reviewer_login = await client.post(
        "/api/v1/admin/auth/login", json={"email": "reviewer@example.com", "password": "adminpass1"}
    )
    reviewer_headers = {"Authorization": f"Bearer {reviewer_login.json()['access_token']}"}

    response = await client.post(
        "/api/v1/admin/jobs", headers=reviewer_headers, json=_job_payload(company_id)
    )
    assert response.status_code == 403


async def test_job_filters_and_search(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    remote_job = await client.post(
        "/api/v1/admin/jobs",
        headers=admin_headers,
        json=_job_payload(company_id, title="Remote Data Analyst", work_mode="REMOTE", country="Kenya"),
    )
    onsite_job = await client.post(
        "/api/v1/admin/jobs",
        headers=admin_headers,
        json=_job_payload(company_id, title="Process Technician", work_mode="ON_SITE", country="Nigeria"),
    )
    for resp in (remote_job, onsite_job):
        job_id = resp.json()["id"]
        await client.put(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"})

    remote_only = await client.get("/api/v1/jobs", params={"work_mode": "REMOTE"})
    assert remote_only.json()["total"] == 1
    assert remote_only.json()["items"][0]["title"] == "Remote Data Analyst"

    nigeria_only = await client.get("/api/v1/jobs", params={"country": "Nigeria"})
    assert nigeria_only.json()["total"] == 1

    search_result = await client.get("/api/v1/jobs", params={"search": "technician"})
    assert search_result.json()["total"] == 1
    assert search_result.json()["items"][0]["title"] == "Process Technician"


async def test_expired_or_inactive_job_hidden_from_public(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    create_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id)
    )
    job_id = create_response.json()["id"]
    await client.put(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"})
    await client.put(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"is_active": False})

    public_detail = await client.get(f"/api/v1/jobs/{job_id}")
    assert public_detail.status_code == 404


async def test_duplicate_job_creates_new_draft(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    original = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id)
    )
    job_id = original.json()["id"]
    await client.put(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"})

    duplicate = await client.post(f"/api/v1/admin/jobs/{job_id}/duplicate", headers=admin_headers)
    assert duplicate.status_code == 200
    body = duplicate.json()
    assert body["id"] != job_id
    assert body["status"] == "DRAFT"
    assert "(Copy)" in body["title"]


async def test_publishing_sets_published_at_once(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    create_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id)
    )
    job_id = create_response.json()["id"]
    assert create_response.json()["published_at"] is None

    publish_response = await client.put(
        f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"}
    )
    first_published_at = publish_response.json()["published_at"]
    assert first_published_at is not None

    # Unpublishing and republishing should not overwrite the original publish timestamp.
    await client.put(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "DRAFT"})
    republish_response = await client.put(
        f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"}
    )
    assert republish_response.json()["published_at"] == first_published_at


async def test_expired_job_hidden_from_public_even_if_still_marked_published(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    create_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id)
    )
    job_id = create_response.json()["id"]
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    await client.put(
        f"/api/v1/admin/jobs/{job_id}",
        headers=admin_headers,
        json={"status": "PUBLISHED", "expires_at": yesterday},
    )

    # Admin never flipped is_active/status — only the expiry date passed. It must still 404
    # publicly rather than relying on someone remembering to archive it.
    public_detail = await client.get(f"/api/v1/jobs/{job_id}")
    assert public_detail.status_code == 404
    public_list = await client.get("/api/v1/jobs")
    assert public_list.json()["total"] == 0


async def test_create_job_rejects_unknown_company(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload("not-a-real-company-id")
    )
    assert response.status_code == 422


async def test_deleting_a_company_with_jobs_is_blocked_not_cascaded(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Phase 9.5 audit hardening: jobs.company_id is ondelete=RESTRICT, not CASCADE — deleting a
    company that still has jobs must fail cleanly (409) rather than silently wiping the jobs and
    orphaning any application history that references them."""
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)
    await client.post("/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id))

    delete_response = await client.delete(f"/api/v1/admin/companies/{company_id}", headers=admin_headers)
    assert delete_response.status_code == 409

    # The company and its job must still be there — nothing was silently removed.
    company_response = await client.get(f"/api/v1/admin/companies/{company_id}", headers=admin_headers)
    assert company_response.status_code == 200
    jobs_response = await client.get("/api/v1/admin/jobs", headers=admin_headers)
    assert jobs_response.json()["total"] == 1
