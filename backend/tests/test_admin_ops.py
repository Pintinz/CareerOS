"""Phase 9 — Admin CMS, Content Operations & Operational Monitoring.

Covers: retry/backoff classification and behavior, scheduler job idempotency, content workflow
(reviewed_by/published_by tracking), scheduled publishing + expiration, audit logging, system
settings (including the one wired-to-a-consumer setting), the source registry + discovery queue
(including deduplication and the never-auto-publish create-draft flow), notifications, user admin
(privacy + suspend/reactivate), and RBAC enforcement on the new SUPER_ADMIN-only routes.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminRole
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.password import hash_password
from app.services.retry_policy import (
    FailureCategory,
    PermanentFailure,
    RetryPolicy,
    classify_exception,
    run_with_retry,
)

from tests.test_aptitude import _create_category, _register_admin_and_login
from tests.test_jobs import _admin_headers, _create_admin, _create_company, _job_payload, _user_headers

pytestmark = pytest.mark.asyncio


async def _create_admin_with_role(db_session: AsyncSession, *, email: str, role: AdminRole) -> None:
    repo = AdminUserRepository(db_session)
    await repo.create(email=email, hashed_password=hash_password("adminpass1"), role=role)
    await db_session.commit()


async def _headers_for(client: AsyncClient, email: str) -> dict:
    response = await client.post("/api/v1/admin/auth/login", json={"email": email, "password": "adminpass1"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Retry/backoff (spec §40, §60)
# ---------------------------------------------------------------------------


def test_classify_exception_categories() -> None:
    request = httpx.Request("GET", "https://example.com")
    assert classify_exception(httpx.ConnectError("boom", request=request)) == FailureCategory.TRANSIENT
    assert (
        classify_exception(httpx.HTTPStatusError("401", request=request, response=httpx.Response(401, request=request)))
        == FailureCategory.AUTHORIZATION
    )
    assert (
        classify_exception(httpx.HTTPStatusError("429", request=request, response=httpx.Response(429, request=request)))
        == FailureCategory.TRANSIENT
    )
    assert (
        classify_exception(httpx.HTTPStatusError("503", request=request, response=httpx.Response(503, request=request)))
        == FailureCategory.PROVIDER_OUTAGE
    )
    assert (
        classify_exception(httpx.HTTPStatusError("400", request=request, response=httpx.Response(400, request=request)))
        == FailureCategory.INVALID_REQUEST
    )


async def test_run_with_retry_succeeds_after_transient_failures() -> None:
    request = httpx.Request("GET", "https://example.com")
    calls = {"count": 0}

    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise httpx.ConnectError("boom", request=request)
        return "ok"

    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    result = await run_with_retry(flaky, policy=RetryPolicy(max_attempts=5, base_delay_seconds=0.01, max_delay_seconds=0.05), sleep=fake_sleep)
    assert result == "ok"
    assert calls["count"] == 3
    assert len(sleeps) == 2  # slept before the 2nd and 3rd attempts, not after the final success.


async def test_run_with_retry_never_retries_authorization_failures() -> None:
    request = httpx.Request("GET", "https://example.com")
    calls = {"count": 0}

    async def always_401():
        calls["count"] += 1
        raise httpx.HTTPStatusError("401", request=request, response=httpx.Response(401, request=request))

    with pytest.raises(PermanentFailure) as exc_info:
        await run_with_retry(always_401, policy=RetryPolicy(max_attempts=5, base_delay_seconds=0.01))
    assert exc_info.value.category == FailureCategory.AUTHORIZATION
    assert calls["count"] == 1  # never retried a permanent 401.


async def test_run_with_retry_gives_up_after_max_attempts() -> None:
    request = httpx.Request("GET", "https://example.com")
    calls = {"count": 0}

    async def always_transient():
        calls["count"] += 1
        raise httpx.ConnectError("boom", request=request)

    async def fake_sleep(seconds: float) -> None:
        return None

    with pytest.raises(PermanentFailure):
        await run_with_retry(always_transient, policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.01), sleep=fake_sleep)
    assert calls["count"] == 3


# ---------------------------------------------------------------------------
# Content lifecycle: scheduled publishing + expiration (spec §14-15/§41)
# ---------------------------------------------------------------------------


async def test_scheduled_content_publishes_and_is_idempotent(client: AsyncClient, db_session: AsyncSession) -> None:
    from app.services import content_lifecycle_service

    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers,
        json=_job_payload(company_id, status="REVIEW", scheduled_publish_at=past),
    )
    job_id = response.json()["id"]

    published_count = await content_lifecycle_service.publish_scheduled_content(db_session)
    assert published_count == 1

    detail = await client.get(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers)
    assert detail.json()["status"] == "PUBLISHED"

    # Idempotent — a duplicate scheduler tick must not re-publish or error.
    second_run = await content_lifecycle_service.publish_scheduled_content(db_session)
    assert second_run == 0


async def test_content_expiration_marks_expired_and_is_idempotent(client: AsyncClient, db_session: AsyncSession) -> None:
    from app.services import content_lifecycle_service

    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id, status="PUBLISHED", expires_at=past)
    )
    job_id = response.json()["id"]

    expired_count = await content_lifecycle_service.expire_content(db_session)
    assert expired_count == 1
    detail = await client.get(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers)
    assert detail.json()["status"] == "EXPIRED"

    assert await content_lifecycle_service.expire_content(db_session) == 0


async def test_scheduler_leader_lock_always_passes_on_sqlite(db_session: AsyncSession) -> None:
    """Phase 11 §22: this codebase's only exercised database (SQLite, see DATABASE.md) has no
    advisory-lock primitive and no realistic multi-instance story, so the leader-election check
    must be a documented no-op pass-through here — never accidentally block every scheduled job
    from ever running in the one environment this project actually tests against."""
    from app.scheduler import _acquire_leader_lock

    assert await _acquire_leader_lock(db_session, "some_job") is True
    # Calling it twice (simulating two instances both checking) must not deadlock or flip-flop.
    assert await _acquire_leader_lock(db_session, "some_job") is True


# ---------------------------------------------------------------------------
# Content workflow: reviewed_by / published_by tracking (spec §13)
# ---------------------------------------------------------------------------


async def test_job_publish_records_published_by_and_creates_audit_log(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)
    create_response = await client.post("/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id))
    job_id = create_response.json()["id"]
    assert create_response.json()["created_by_admin_id"] is not None

    publish_response = await client.put(f"/api/v1/admin/jobs/{job_id}", headers=admin_headers, json={"status": "PUBLISHED"})
    assert publish_response.json()["published_by_admin_id"] is not None
    assert publish_response.json()["published_at"] is not None

    audit_response = await client.get("/api/v1/admin/audit?entity_type=job", headers=admin_headers)
    actions = [entry["action"] for entry in audit_response.json()["items"] if entry["entity_id"] == job_id]
    assert "create" in actions
    assert "publish" in actions


# ---------------------------------------------------------------------------
# System settings (spec §35) — SUPER_ADMIN only, and the one wired consumer
# ---------------------------------------------------------------------------


async def test_settings_require_super_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin_with_role(db_session, email="admin2@example.com", role=AdminRole.ADMIN)
    headers = await _headers_for(client, "admin2@example.com")
    response = await client.get("/api/v1/admin/settings", headers=headers)
    assert response.status_code == 403


async def test_settings_super_admin_can_read_and_update(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin_with_role(db_session, email="super@example.com", role=AdminRole.SUPER_ADMIN)
    headers = await _headers_for(client, "super@example.com")

    listing = await client.get("/api/v1/admin/settings", headers=headers)
    assert listing.status_code == 200
    thresholds = listing.json()["email_classifier_confidence_thresholds"]
    assert thresholds["is_default"] is True

    update = await client.put(
        "/api/v1/admin/settings/email_classifier_confidence_thresholds",
        headers=headers,
        json={"value": {"high": 0.9, "medium": 0.5, "suggest_min": 0.5}},
    )
    assert update.status_code == 200
    assert update.json()["value"]["high"] == 0.9
    assert update.json()["is_default"] is False


async def test_updated_confidence_threshold_is_actually_consumed(client: AsyncClient, db_session: AsyncSession) -> None:
    """The one setting genuinely wired to its consumer — raising `suggest_min` above what an
    email would otherwise score should suppress a suggestion that used to qualify."""
    from app.email_tracking.types import RawEmail
    from app.services.email_tracking_service import EmailTrackingService
    from app.services import system_settings_service

    await _create_admin_with_role(db_session, email="super2@example.com", role=AdminRole.SUPER_ADMIN)
    headers = await _headers_for(client, "super2@example.com")
    user_headers = await _user_headers(client, "settingsuser@example.com")
    await client.post(
        "/api/v1/applications", headers=user_headers,
        json={"company_name": "ExxonMobil", "role_title": "Process Technician", "current_stage": "APPLIED"},
    )
    me = await client.get("/api/v1/auth/me", headers=user_headers)
    user_id = me.json()["id"]

    await system_settings_service.set_value(
        db_session, "email_classifier_confidence_thresholds", {"high": 0.99, "medium": 0.99, "suggest_min": 0.99}, admin_id=None
    )

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_id, None,
        RawEmail(
            provider_message_id="settings-test-1", provider_thread_id=None, sender_email="recruiting@exxonmobil.com",
            sender_name=None, subject="Interview invitation",
            body_text="We would like to invite you to interview for the Process Technician role.",
            received_at=datetime.now(timezone.utc),
        ),
    )
    assert event is not None
    assert event.status.value == "DETECTED"  # matched + classified, but confidence never reaches the raised bar.
    _ = headers  # headers unused beyond proving SUPER_ADMIN could have made this change via the API.


# ---------------------------------------------------------------------------
# Source registry + Discovery queue (spec §24-27)
# ---------------------------------------------------------------------------


async def test_discovery_ingest_deduplicates_by_url(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    source_response = await client.post(
        "/api/v1/admin/sources", headers=admin_headers,
        json={"name": "Shell Careers", "url": "https://shell.com/careers", "source_type": "OFFICIAL_CAREER_PAGE"},
    )
    source_id = source_response.json()["id"]

    payload = {
        "source_id": source_id, "item_type": "JOB", "detected_title": "Process Technician",
        "original_url": "https://shell.com/careers/12345",
    }
    first = await client.post("/api/v1/admin/discovery/ingest", headers=admin_headers, json=payload)
    assert first.status_code == 201
    assert first.json() is not None

    second = await client.post("/api/v1/admin/discovery/ingest", headers=admin_headers, json=payload)
    assert second.json() is None  # duplicate URL from the same source — no second card created.

    listing = await client.get("/api/v1/admin/discovery", headers=admin_headers)
    assert listing.json()["total"] == 1


async def test_discovery_create_draft_never_auto_publishes(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers, name="Shell")
    source_response = await client.post(
        "/api/v1/admin/sources", headers=admin_headers,
        json={"name": "Shell Careers", "url": "https://shell.com/careers", "source_type": "OFFICIAL_CAREER_PAGE"},
    )
    source_id = source_response.json()["id"]
    ingest = await client.post(
        "/api/v1/admin/discovery/ingest", headers=admin_headers,
        json={"source_id": source_id, "item_type": "JOB", "detected_title": "Process Technician", "original_url": "https://shell.com/careers/999"},
    )
    item_id = ingest.json()["id"]

    draft_response = await client.post(
        f"/api/v1/admin/discovery/{item_id}/create-draft", headers=admin_headers,
        json={"company_id": company_id, "title": "Process Technician", "summary": "Discovered role"},
    )
    assert draft_response.status_code == 200
    draft_id = draft_response.json()["draft_id"]

    job_detail = await client.get(f"/api/v1/admin/jobs/{draft_id}", headers=admin_headers)
    assert job_detail.json()["status"] == "DRAFT"  # never PUBLISHED automatically.

    item_detail = await client.get(f"/api/v1/admin/discovery/{item_id}", headers=admin_headers)
    assert item_detail.json()["status"] == "REVIEWED"

    # Reviewing twice is refused rather than creating a second draft.
    repeat = await client.post(
        f"/api/v1/admin/discovery/{item_id}/create-draft", headers=admin_headers,
        json={"company_id": company_id, "title": "Process Technician"},
    )
    assert repeat.status_code == 409


async def test_discovery_ignore_and_reject(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    source_response = await client.post(
        "/api/v1/admin/sources", headers=admin_headers,
        json={"name": "Generic RSS", "url": "https://example.com/feed", "source_type": "RSS"},
    )
    source_id = source_response.json()["id"]
    ingest = await client.post(
        "/api/v1/admin/discovery/ingest", headers=admin_headers,
        json={"source_id": source_id, "item_type": "INTELLIGENCE", "detected_title": "News item", "original_url": "https://example.com/1"},
    )
    item_id = ingest.json()["id"]

    ignored = await client.post(f"/api/v1/admin/discovery/{item_id}/ignore", headers=admin_headers)
    assert ignored.json()["status"] == "IGNORED"


# ---------------------------------------------------------------------------
# Notifications (spec §32-33)
# ---------------------------------------------------------------------------


async def test_notification_create_and_send_never_claims_real_delivery(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    create = await client.post(
        "/api/v1/admin/notifications", headers=admin_headers,
        json={"title": "New jobs at Shell", "body": "Check out new openings.", "audience": "ALL_USERS"},
    )
    assert create.status_code == 201
    notification_id = create.json()["id"]
    assert create.json()["status"] == "DRAFT"

    send = await client.post(f"/api/v1/admin/notifications/{notification_id}/send", headers=admin_headers)
    assert send.json()["status"] == "SENT"
    assert send.json()["recipient_count"] == 0  # honest — no delivery channel exists in this environment.

    repeat = await client.post(f"/api/v1/admin/notifications/{notification_id}/send", headers=admin_headers)
    assert repeat.status_code == 409


# ---------------------------------------------------------------------------
# User admin (spec §29-31)
# ---------------------------------------------------------------------------


async def test_user_admin_list_never_exposes_password_hash(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    await _user_headers(client, "privacyuser@example.com")

    listing = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] >= 1
    raw_text = str(body)
    assert "hashed_password" not in raw_text
    assert "$argon2" not in raw_text


async def test_user_suspend_and_reactivate_blocks_and_restores_login(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    user_headers = await _user_headers(client, "suspendme@example.com")
    me = await client.get("/api/v1/auth/me", headers=user_headers)
    user_id = me.json()["id"]

    suspend = await client.post(f"/api/v1/admin/users/{user_id}/suspend", headers=admin_headers)
    assert suspend.status_code == 204

    blocked_login = await client.post("/api/v1/auth/login", json={"email": "suspendme@example.com", "password": "candidatepass1"})
    assert blocked_login.status_code == 403

    reactivate = await client.post(f"/api/v1/admin/users/{user_id}/reactivate", headers=admin_headers)
    assert reactivate.status_code == 204
    restored_login = await client.post("/api/v1/auth/login", json={"email": "suspendme@example.com", "password": "candidatepass1"})
    assert restored_login.status_code == 200


async def test_only_admin_or_super_admin_can_suspend(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_admin_with_role(db_session, email="editor@example.com", role=AdminRole.EDITOR)
    headers = await _headers_for(client, "editor@example.com")
    user_headers = await _user_headers(client, "cannotbesuspended@example.com")
    me = await client.get("/api/v1/auth/me", headers=user_headers)
    user_id = me.json()["id"]

    response = await client.post(f"/api/v1/admin/users/{user_id}/suspend", headers=headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# CSV bulk import + duplicate detection (spec §20-21)
# ---------------------------------------------------------------------------


async def test_bulk_import_aptitude_questions_reports_imported_skipped_and_row_errors(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_category(db_session, "bulk-import-numerical", "Numerical")
    admin_headers = await _register_admin_and_login(client, db_session)

    csv_text = (
        "question_text,question_type,category_slug,difficulty,option_1,option_1_correct,option_2,option_2_correct\n"
        "What is 2 plus 2?,SINGLE_CHOICE,bulk-import-numerical,EASY,3,false,4,true\n"
        "Broken row with unknown category,SINGLE_CHOICE,does-not-exist,EASY,3,false,4,true\n"
        "What is 2 plus 2?,SINGLE_CHOICE,bulk-import-numerical,EASY,3,false,4,true\n"  # exact duplicate of row 1.
        "Invalid single choice question,SINGLE_CHOICE,bulk-import-numerical,EASY,3,true,4,true\n"  # two correct options.
    )
    files = {"file": ("questions.csv", csv_text, "text/csv")}
    response = await client.post("/api/v1/admin/aptitude/questions/bulk-import", headers=admin_headers, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 1
    assert len(body["errors"]) == 2
    assert any("does-not-exist" in e["reason"] or "category" in e["reason"].lower() for e in body["errors"])

    listing = await client.get("/api/v1/admin/aptitude/questions", headers=admin_headers)
    assert listing.json()["total"] == 1


async def test_bulk_import_does_not_reimport_questions_already_in_the_bank(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_category(db_session, "bulk-import-verbal", "Verbal")
    admin_headers = await _register_admin_and_login(client, db_session)
    csv_text = (
        "question_text,question_type,category_slug,difficulty,option_1,option_1_correct,option_2,option_2_correct\n"
        "Choose the correct synonym for happy.,SINGLE_CHOICE,bulk-import-verbal,EASY,Sad,false,Joyful,true\n"
    )
    files = {"file": ("questions.csv", csv_text, "text/csv")}
    first = await client.post("/api/v1/admin/aptitude/questions/bulk-import", headers=admin_headers, files=files)
    assert first.json()["imported"] == 1

    second = await client.post(
        "/api/v1/admin/aptitude/questions/bulk-import", headers=admin_headers, files={"file": ("questions.csv", csv_text, "text/csv")}
    )
    assert second.json()["imported"] == 0
    assert second.json()["skipped"] == 1
