import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_jobs import _admin_headers, _create_admin, _create_company, _job_payload, _user_headers

pytestmark = pytest.mark.asyncio


async def test_create_manual_application_requires_company_and_role(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    response = await client.post("/api/v1/applications", headers=headers, json={})
    assert response.status_code == 422


async def test_create_manual_application_and_initial_timeline_event(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    response = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company_name": "Acme Corp", "role_title": "Process Technician", "current_stage": "SAVED"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["company_name"] == "Acme Corp"
    assert body["current_stage"] == "SAVED"

    detail = await client.get(f"/api/v1/applications/{body['id']}", headers=headers)
    assert detail.status_code == 200
    timeline = detail.json()["timeline"]
    assert len(timeline) == 1
    assert timeline[0]["stage"] == "SAVED"


async def test_create_application_from_real_job_prefills_fields(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers, name="ExxonMobil")
    job_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id, title="Process Technician")
    )
    job_id = job_response.json()["id"]
    await client.put(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"})

    user_headers = await _user_headers(client)
    response = await client.post(
        "/api/v1/applications", headers=user_headers, json={"job_id": job_id, "current_stage": "APPLIED"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["company_name"] == "ExxonMobil"
    assert body["role_title"] == "Process Technician"
    assert body["job_id"] == job_id


async def test_applications_are_isolated_per_user(client: AsyncClient) -> None:
    headers_a = await _user_headers(client, "a@example.com")
    headers_b = await _user_headers(client, "b@example.com")

    create_response = await client.post(
        "/api/v1/applications",
        headers=headers_a,
        json={"company_name": "Acme Corp", "role_title": "Engineer"},
    )
    application_id = create_response.json()["id"]

    # User B cannot see or modify user A's application.
    get_as_b = await client.get(f"/api/v1/applications/{application_id}", headers=headers_b)
    assert get_as_b.status_code == 404

    update_as_b = await client.put(
        f"/api/v1/applications/{application_id}", headers=headers_b, json={"salary": "999999"}
    )
    assert update_as_b.status_code == 404

    list_as_b = await client.get("/api/v1/applications", headers=headers_b)
    assert list_as_b.json()["total"] == 0

    list_as_a = await client.get("/api/v1/applications", headers=headers_a)
    assert list_as_a.json()["total"] == 1


async def test_stage_update_appends_timeline_event_and_updates_current_stage(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    create_response = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company_name": "Acme Corp", "role_title": "Engineer", "current_stage": "APPLIED"},
    )
    application_id = create_response.json()["id"]

    stage_response = await client.post(
        f"/api/v1/applications/{application_id}/stage",
        headers=headers,
        json={"stage": "INTERVIEW", "note": "Recruiter called to schedule"},
    )
    assert stage_response.status_code == 200
    body = stage_response.json()
    assert body["current_stage"] == "INTERVIEW"
    assert len(body["timeline"]) == 2
    assert body["timeline"][0]["stage"] == "APPLIED"
    assert body["timeline"][1]["stage"] == "INTERVIEW"
    assert body["timeline"][1]["note"] == "Recruiter called to schedule"


async def test_add_and_list_notes(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    create_response = await client.post(
        "/api/v1/applications", headers=headers, json={"company_name": "Acme Corp", "role_title": "Engineer"}
    )
    application_id = create_response.json()["id"]

    note_response = await client.post(
        f"/api/v1/applications/{application_id}/notes", headers=headers, json={"text": "Follow up next week"}
    )
    assert note_response.status_code == 201

    detail = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert len(detail.json()["notes"]) == 1
    assert detail.json()["notes"][0]["text"] == "Follow up next week"


async def test_filter_applications_by_stage(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company_name": "Acme Corp", "role_title": "Engineer", "current_stage": "APPLIED"},
    )
    await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company_name": "Globex", "role_title": "Analyst", "current_stage": "INTERVIEW"},
    )

    filtered = await client.get("/api/v1/applications", params={"stage": "INTERVIEW"}, headers=headers)
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["company_name"] == "Globex"


async def test_active_applications_summary_excludes_terminal_stages(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    active = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company_name": "Acme Corp", "role_title": "Engineer", "current_stage": "INTERVIEW"},
    )
    rejected = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company_name": "Globex", "role_title": "Analyst", "current_stage": "APPLIED"},
    )
    await client.post(
        f"/api/v1/applications/{rejected.json()['id']}/stage", headers=headers, json={"stage": "REJECTED"}
    )

    summary = await client.get("/api/v1/me/applications-summary", headers=headers)
    assert summary.json()["active_applications"] == 1
    assert active.json()["current_stage"] == "INTERVIEW"


async def test_delete_application(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    create_response = await client.post(
        "/api/v1/applications", headers=headers, json={"company_name": "Acme Corp", "role_title": "Engineer"}
    )
    application_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/applications/{application_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert get_response.status_code == 404
