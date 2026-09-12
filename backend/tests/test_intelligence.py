import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_jobs import _admin_headers, _create_admin, _create_company, _user_headers

pytestmark = pytest.mark.asyncio


def _post_payload(**overrides) -> dict:
    payload = {
        "headline": "ExxonMobil announces refinery automation upgrade",
        "category": "AUTOMATION",
        "summary": "New PLC-based automation systems being rolled out across the Lagos refinery.",
        "why_it_matters": "May increase relevance of PLC/automation skills for future postings.",
        "relevant_roles": ["Process Technician", "Automation Engineer"],
    }
    payload.update(overrides)
    return payload


async def test_full_intelligence_acceptance_workflow(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    create_response = await client.post(
        "/api/v1/admin/intelligence", headers=admin_headers, json=_post_payload(company_id=company_id)
    )
    assert create_response.status_code == 201
    post_id = create_response.json()["id"]
    assert create_response.json()["status"] == "DRAFT"

    public_list = await client.get("/api/v1/intelligence")
    assert public_list.json()["total"] == 0

    publish_response = await client.put(
        f"/api/v1/admin/intelligence/{post_id}", headers=admin_headers, json={"status": "PUBLISHED"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["published_at"] is not None

    public_list = await client.get("/api/v1/intelligence")
    body = public_list.json()
    assert body["total"] == 1
    assert body["items"][0]["headline"] == _post_payload()["headline"]
    assert body["items"][0]["company"]["name"] is not None

    public_detail = await client.get(f"/api/v1/intelligence/{post_id}")
    assert public_detail.status_code == 200
    assert "may increase relevance" in public_detail.json()["why_it_matters"].lower()


async def test_intelligence_category_filter(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)

    automation = await client.post(
        "/api/v1/admin/intelligence", headers=admin_headers, json=_post_payload(category="AUTOMATION")
    )
    hiring = await client.post(
        "/api/v1/admin/intelligence",
        headers=admin_headers,
        json=_post_payload(headline="Company announces graduate hiring drive", category="HIRING"),
    )
    for resp in (automation, hiring):
        pid = resp.json()["id"]
        await client.put(f"/api/v1/admin/intelligence/{pid}", headers=admin_headers, json={"status": "PUBLISHED"})

    hiring_only = await client.get("/api/v1/intelligence", params={"category": "HIRING"})
    assert hiring_only.json()["total"] == 1
    assert hiring_only.json()["items"][0]["category"] == "HIRING"


async def test_follow_company_and_filter_intelligence_by_followed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    followed_company_id = await _create_company(client, admin_headers, name="Followed Co")
    other_company_id = await _create_company(client, admin_headers, name="Other Co")

    followed_post = await client.post(
        "/api/v1/admin/intelligence", headers=admin_headers, json=_post_payload(company_id=followed_company_id)
    )
    other_post = await client.post(
        "/api/v1/admin/intelligence",
        headers=admin_headers,
        json=_post_payload(headline="Other Co news", company_id=other_company_id),
    )
    for resp in (followed_post, other_post):
        pid = resp.json()["id"]
        await client.put(f"/api/v1/admin/intelligence/{pid}", headers=admin_headers, json={"status": "PUBLISHED"})

    user_headers = await _user_headers(client)

    follow_response = await client.post(f"/api/v1/companies/{followed_company_id}/follow", headers=user_headers)
    assert follow_response.status_code == 204

    company_detail = await client.get(f"/api/v1/companies/{followed_company_id}", headers=user_headers)
    assert company_detail.json()["is_following"] is True

    followed_feed = await client.get(
        "/api/v1/intelligence", params={"followed_only": True}, headers=user_headers
    )
    body = followed_feed.json()
    assert body["total"] == 1
    assert body["items"][0]["headline"] == _post_payload()["headline"]

    followed_companies = await client.get("/api/v1/me/followed-companies", headers=user_headers)
    assert len(followed_companies.json()) == 1
    assert followed_companies.json()[0]["id"] == followed_company_id

    unfollow_response = await client.delete(f"/api/v1/companies/{followed_company_id}/follow", headers=user_headers)
    assert unfollow_response.status_code == 204
    followed_companies_after = await client.get("/api/v1/me/followed-companies", headers=user_headers)
    assert len(followed_companies_after.json()) == 0


async def test_reviewer_cannot_publish_intelligence(client: AsyncClient, db_session: AsyncSession) -> None:
    from app.models.admin_user import AdminRole
    from app.repositories.admin_user_repository import AdminUserRepository
    from app.security.password import hash_password

    repo = AdminUserRepository(db_session)
    await repo.create(
        email="reviewer@example.com", hashed_password=hash_password("adminpass1"), role=AdminRole.REVIEWER
    )
    await db_session.commit()
    login = await client.post(
        "/api/v1/admin/auth/login", json={"email": "reviewer@example.com", "password": "adminpass1"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post("/api/v1/admin/intelligence", headers=headers, json=_post_payload())
    assert response.status_code == 403


async def test_jobs_filtered_by_company_id(client: AsyncClient, db_session: AsyncSession) -> None:
    from tests.test_jobs import _job_payload

    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_a = await _create_company(client, admin_headers, name="Company A")
    company_b = await _create_company(client, admin_headers, name="Company B")

    job_a = await client.post("/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_a))
    job_b = await client.post("/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_b))
    for resp in (job_a, job_b):
        jid = resp.json()["id"]
        await client.put(f"/api/v1/admin/jobs/{jid}", headers=admin_headers, json={"status": "PUBLISHED"})

    filtered = await client.get("/api/v1/jobs", params={"company_id": company_a})
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["company"]["name"] == "Company A"
