"""Phase 9.5 audit — focused cross-feature E2E journeys (spec item 54).

Journey A (admin publish -> mobile fetch -> save -> application -> stage update) is the one gap
not already covered end-to-end by an existing single test, so it gets a dedicated one here.

Journeys B, C, and D are each already covered end-to-end by an existing test elsewhere, and are
not duplicated here — see SYSTEM_AUDIT.md for the full mapping:
  - Journey B (application Aptitude stage -> prepare -> complete test -> results):
    tests/test_aptitude.py::test_application_linked_session_does_not_mutate_application_stage
    + tests/test_aptitude.py::test_submit_grades_with_negative_marking_and_unanswered
  - Journey C (application Interview stage -> prepare -> STAR -> session completion):
    tests/test_interview.py::test_application_linked_session_resolves_job_and_does_not_mutate_stage
    + tests/test_interview.py::test_answering_and_completion_computes_stats
    + tests/test_interview.py::test_star_story_crud_and_isolation (STAR creation)
  - Journey D (mock recruitment email -> suggested stage -> user confirms -> timeline updates):
    tests/test_email_tracking.py::test_full_flow_matched_suggestion_confirm_updates_real_stage
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_admin(db_session: AsyncSession) -> None:
    repo = AdminUserRepository(db_session)
    await repo.create(email="e2e-admin@example.com", hashed_password=hash_password("adminpass1"), role=AdminRole.ADMIN)
    await db_session.commit()


async def _admin_headers(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "e2e-admin@example.com", "password": "adminpass1"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _user_headers(client: AsyncClient, email: str = "e2e-candidate@example.com") -> dict:
    response = await client.post("/api/v1/auth/register", json={"email": email, "password": "candidatepass1"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_journey_a_admin_publish_to_mobile_save_to_application_stage_update(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Admin publishes a job -> the public/mobile feed sees it -> a user saves it -> creates a
    real application from it -> updates that application's stage -> the timeline reflects it.
    No dead links, no duplicated records, no state left inconsistent at any step."""
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)

    company_response = await client.post(
        "/api/v1/admin/companies", headers=admin_headers, json={"name": "Journey Co"}
    )
    company_id = company_response.json()["id"]

    job_response = await client.post(
        "/api/v1/admin/jobs",
        headers=admin_headers,
        json={
            "company_id": company_id,
            "title": "Field Engineer",
            "employment_type": "FULL_TIME",
            "work_mode": "ON_SITE",
            "application_url": "https://careers.example.com/apply/42",
        },
    )
    assert job_response.status_code == 201
    job = job_response.json()
    assert job["status"] == "DRAFT"

    # Not visible to a mobile user while still a draft.
    public_list = await client.get("/api/v1/jobs")
    assert public_list.json()["total"] == 0

    publish_response = await client.put(
        f"/api/v1/admin/jobs/{job['id']}", headers=admin_headers, json={"status": "PUBLISHED"}
    )
    assert publish_response.status_code == 200

    # Now visible, and the admin who published it is recorded (Phase 9 workflow tracking).
    published_job = await client.get(f"/api/v1/admin/jobs/{job['id']}", headers=admin_headers)
    assert published_job.json()["published_by_admin_id"] is not None

    public_list = await client.get("/api/v1/jobs")
    body = public_list.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == job["id"]

    # A mobile user saves it.
    user_headers = await _user_headers(client)
    save_response = await client.post(f"/api/v1/jobs/{job['id']}/save", headers=user_headers)
    assert save_response.status_code == 204

    saved_list = await client.get("/api/v1/jobs", params={"saved_only": True}, headers=user_headers)
    assert saved_list.json()["total"] == 1

    # Creates a real application from the saved job — never a second, unrelated job record.
    application_response = await client.post(
        "/api/v1/applications", headers=user_headers, json={"job_id": job["id"]}
    )
    assert application_response.status_code == 201
    application = application_response.json()
    assert application["job_id"] == job["id"]
    assert application["current_stage"] == "SAVED"

    # Updates the application's stage through the one legitimate path.
    stage_response = await client.post(
        f"/api/v1/applications/{application['id']}/stage",
        headers=user_headers,
        json={"stage": "APPLIED", "note": "Submitted via company careers page."},
    )
    assert stage_response.status_code == 200
    detail = stage_response.json()
    assert detail["current_stage"] == "APPLIED"
    assert detail["timeline"][-1]["stage"] == "APPLIED"
    assert detail["timeline"][-1]["source"] == "MANUAL"

    # Editing the job afterward doesn't retroactively corrupt the application's own record of it.
    await client.put(
        f"/api/v1/admin/jobs/{job['id']}", headers=admin_headers, json={"title": "Senior Field Engineer"}
    )
    unchanged_application = await client.get(f"/api/v1/applications/{application['id']}", headers=user_headers)
    assert unchanged_application.json()["role_title"] == "Field Engineer"

    # Archiving the job removes it from normal discovery without touching the application.
    await client.put(f"/api/v1/admin/jobs/{job['id']}", headers=admin_headers, json={"status": "ARCHIVED"})
    archived_public_list = await client.get("/api/v1/jobs")
    assert archived_public_list.json()["total"] == 0
    still_there = await client.get(f"/api/v1/applications/{application['id']}", headers=user_headers)
    assert still_there.status_code == 200
    assert still_there.json()["current_stage"] == "APPLIED"
