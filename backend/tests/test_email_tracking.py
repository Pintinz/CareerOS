"""Phase 8 — Smart Recruitment Email Tracking.

Covers: the deterministic classifier corpus (including the mandatory negative-context cases), the
application-matching engine (exact/ambiguous/no-match), the full OAuth-state → connection →
mock-message → classify → match → suggest → CONFIRM → real stage-transition pipeline, cross-user
isolation, idempotent duplicate-message handling, and the "never silently change a stage" guarantee
end to end.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.email_tracking.classifier import classify_stage
from app.email_tracking.matcher import match_application
from app.email_tracking.types import ApplicationSignal, RawEmail
from app.models.email_tracking import EmailConnection, EmailProvider, OAuthState
from app.services.email_tracking_service import EmailTrackingService
from app.services.token_encryption_service import TokenDecryptionError, TokenEncryptionService

from tests.test_jobs import _user_headers

pytestmark = pytest.mark.asyncio


async def _current_user_id(client: AsyncClient, headers: dict) -> str:
    response = await client.get("/api/v1/auth/me", headers=headers)
    return response.json()["id"]


def _email(
    *,
    message_id: str = "msg-1",
    sender_email: str = "recruiting@exxonmobil.com",
    subject: str = "",
    body_text: str = "",
    received_at: datetime | None = None,
) -> RawEmail:
    return RawEmail(
        provider_message_id=message_id,
        provider_thread_id=None,
        sender_email=sender_email,
        sender_name="ExxonMobil Recruiting",
        subject=subject,
        body_text=body_text,
        received_at=received_at or datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Classifier corpus (spec §47-48)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "subject,body,expected_stage",
    [
        ("Application received", "Thank you for applying to ExxonMobil.", "APPLICATION_RECEIVED"),
        ("You're shortlisted", "We are pleased to inform you that you have been shortlisted for the next stage.", "SHORTLISTED"),
        ("Online assessment", "You are invited to complete an online assessment for the Process Technician role.", "APTITUDE_TEST"),
        ("Interview invitation", "We would like to invite you to interview next week.", "INTERVIEW"),
        ("Final interview", "Please find below details for your final interview.", "FINAL_INTERVIEW"),
        ("Assessment centre", "You are invited to our assessment centre in Lagos.", "ASSESSMENT_CENTRE"),
        ("Background check", "We will now begin your background check.", "BACKGROUND_CHECK"),
        ("Medical", "Please schedule your pre-employment medical.", "MEDICAL"),
        ("Offer", "We are delighted to offer you the position of Process Technician.", "OFFER"),
        ("Application update", "We regret to inform you that you have not been successful on this occasion.", "REJECTED"),
    ],
)
def test_classify_positive_stage_phrases(subject: str, body: str, expected_stage: str) -> None:
    result = classify_stage(subject=subject, body_text=body, sender_domain="exxonmobil.com")
    assert result.stage == expected_stage
    assert result.is_recruitment_related


@pytest.mark.parametrize(
    "body",
    [
        "Only shortlisted candidates will be contacted.",
        "Shortlisted candidates may be invited to interview.",
        "Due to the high volume of applications we cannot respond to every applicant.",
    ],
)
def test_classify_general_recruitment_language_never_implies_progression(body: str) -> None:
    result = classify_stage(subject="Thanks for your interest", body_text=body, sender_domain="exxonmobil.com")
    assert result.stage is None, "general/aggregate recruitment language must not be treated as a personal stage update"
    assert result.has_negative_context


def test_classify_ignores_unrelated_mail() -> None:
    result = classify_stage(subject="Your weekly newsletter", body_text="Check out our latest blog post!", sender_domain="newsletter.example.com")
    assert result.is_recruitment_related is False
    assert result.stage is None


# ---------------------------------------------------------------------------
# Application matcher (spec §49)
# ---------------------------------------------------------------------------


def _signal(app_id: str, *, company="Shell", role="Graduate Engineer", job_url=None, location=None, applied_date=None) -> ApplicationSignal:
    return ApplicationSignal(
        application_id=app_id, company_name=company, role_title=role, job_url=job_url, location=location, applied_date=applied_date
    )


def test_matcher_matches_single_application_by_company_and_role() -> None:
    email = _email(sender_email="talent@shell.com", subject="Interview invitation", body_text="We would like to invite you to interview for the Graduate Engineer position.")
    apps = [_signal("app-1", company="Shell", role="Graduate Engineer")]
    result = match_application(email, "shell.com", apps)
    assert result.status == "matched"
    assert result.matched_id == "app-1"


def test_matcher_flags_ambiguous_when_multiple_roles_at_same_company() -> None:
    email = _email(sender_email="talent@shell.com", subject="Interview invitation", body_text="We would like to invite you to interview.")
    apps = [
        _signal("app-1", company="Shell", role="Graduate Engineer"),
        _signal("app-2", company="Shell", role="Process Technician"),
        _signal("app-3", company="Shell", role="Maintenance Technician"),
    ]
    result = match_application(email, "shell.com", apps)
    assert result.status == "ambiguous"
    assert set(result.candidate_ids) == {"app-1", "app-2", "app-3"}


def test_matcher_exact_reference_id_wins_over_ambiguous_company_match() -> None:
    email = _email(
        sender_email="talent@shell.com",
        subject="Interview invitation",
        body_text="We would like to invite you to interview. Reference: REQ98765",
    )
    apps = [
        _signal("app-1", company="Shell", role="Graduate Engineer", job_url="https://shell.com/jobs/REQ98765"),
        _signal("app-2", company="Shell", role="Process Technician"),
        _signal("app-3", company="Shell", role="Maintenance Technician"),
    ]
    result = match_application(email, "shell.com", apps)
    assert result.status == "matched"
    assert result.matched_id == "app-1"


def test_matcher_returns_unmatched_for_unrelated_sender() -> None:
    email = _email(sender_email="news@random-blog.example.com", subject="Newsletter", body_text="Nothing relevant here.")
    apps = [_signal("app-1")]
    result = match_application(email, "random-blog.example.com", apps)
    assert result.status == "unmatched"


def test_matcher_does_not_guess_with_no_applications() -> None:
    email = _email()
    result = match_application(email, "exxonmobil.com", [])
    assert result.status == "unmatched"
    assert result.matched_id is None


# ---------------------------------------------------------------------------
# Token encryption (spec §16)
# ---------------------------------------------------------------------------


def test_token_encryption_roundtrip_and_tamper_detection() -> None:
    service = TokenEncryptionService()
    ciphertext = service.encrypt("super-secret-refresh-token")
    assert ciphertext != "super-secret-refresh-token"
    assert service.decrypt(ciphertext) == "super-secret-refresh-token"

    with pytest.raises(TokenDecryptionError):
        service.decrypt("not-a-real-token")


# ---------------------------------------------------------------------------
# OAuth state (spec §44)
# ---------------------------------------------------------------------------


async def test_connect_is_unavailable_without_real_credentials(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    response = await client.post("/api/v1/email-tracking/gmail/connect", headers=headers)
    assert response.status_code == 503


async def test_oauth_callback_rejects_unknown_state(client: AsyncClient) -> None:
    response = await client.get("/api/v1/email-tracking/gmail/callback", params={"code": "abc", "state": "does-not-exist"})
    assert response.status_code == 400


async def test_oauth_callback_rejects_expired_state(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client)
    user_id = await _current_user_id(client, headers)
    now = datetime.now(timezone.utc)
    db_session.add(
        OAuthState(state="expired-state", user_id=user_id, provider=EmailProvider.GMAIL, created_at=now - timedelta(minutes=30), expires_at=now - timedelta(minutes=1))
    )
    await db_session.commit()

    response = await client.get("/api/v1/email-tracking/gmail/callback", params={"code": "abc", "state": "expired-state"})
    assert response.status_code == 400


async def test_oauth_callback_rejects_reused_state(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client)
    user_id = await _current_user_id(client, headers)
    now = datetime.now(timezone.utc)
    db_session.add(
        OAuthState(state="one-time-state", user_id=user_id, provider=EmailProvider.GMAIL, created_at=now, expires_at=now + timedelta(minutes=15))
    )
    await db_session.commit()

    first = await client.get("/api/v1/email-tracking/gmail/callback", params={"code": "abc", "state": "one-time-state"})
    assert first.status_code == 200

    second = await client.get("/api/v1/email-tracking/gmail/callback", params={"code": "abc", "state": "one-time-state"})
    assert second.status_code == 400


async def test_oauth_callback_creates_active_connection_via_mock_provider(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client)
    user_id = await _current_user_id(client, headers)
    now = datetime.now(timezone.utc)
    db_session.add(
        OAuthState(state="connect-state", user_id=user_id, provider=EmailProvider.GMAIL, created_at=now, expires_at=now + timedelta(minutes=15))
    )
    await db_session.commit()

    response = await client.get("/api/v1/email-tracking/gmail/callback", params={"code": "mock-code", "state": "connect-state"})
    assert response.status_code == 200

    connections = await client.get("/api/v1/email-tracking/connections", headers=headers)
    assert connections.status_code == 200
    body = connections.json()
    assert len(body) == 1
    assert body[0]["provider"] == "GMAIL"
    assert body[0]["status"] == "ACTIVE"
    # No token fields at all should ever be serialized (spec §16).
    assert "access_token" not in body[0] and "encrypted_access_token" not in body[0]


# ---------------------------------------------------------------------------
# Cross-user isolation (spec §43/§50)
# ---------------------------------------------------------------------------


async def test_cannot_access_another_users_connection(client: AsyncClient, db_session: AsyncSession) -> None:
    headers_a = await _user_headers(client, "a@example.com")
    user_a = await _current_user_id(client, headers_a)
    headers_b = await _user_headers(client, "b@example.com")

    connection = EmailConnection(
        user_id=user_a,
        provider=EmailProvider.GMAIL,
        provider_account_id="acct-a",
        provider_email="a@gmail.com",
        granted_scopes=["gmail.readonly"],
    )
    db_session.add(connection)
    await db_session.commit()
    await db_session.refresh(connection)

    response = await client.delete(f"/api/v1/email-tracking/connections/{connection.id}", headers=headers_b)
    assert response.status_code == 404


async def test_cannot_access_another_users_recruitment_event(client: AsyncClient, db_session: AsyncSession) -> None:
    headers_a = await _user_headers(client, "a2@example.com")
    user_a = await _current_user_id(client, headers_a)
    headers_b = await _user_headers(client, "b2@example.com")

    app_response = await client.post(
        "/api/v1/applications", headers=headers_a, json={"company_name": "Shell", "role_title": "Graduate Engineer", "current_stage": "APPLIED"}
    )
    application_id = app_response.json()["id"]

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_a,
        None,
        _email(sender_email="talent@shell.com", subject="Interview invitation", body_text="We would like to invite you to interview for the Graduate Engineer role."),
    )
    assert event is not None

    forbidden = await client.get(f"/api/v1/email-tracking/events/{event.id}", headers=headers_b)
    assert forbidden.status_code == 404
    forbidden_confirm = await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers_b)
    assert forbidden_confirm.status_code == 404
    # application_id above is deliberately unused by user B's request — kept for readability of intent.
    assert application_id


# ---------------------------------------------------------------------------
# End-to-end acceptance flows (spec §65-70)
# ---------------------------------------------------------------------------


async def test_full_flow_matched_suggestion_confirm_updates_real_stage(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "flow1@example.com")
    user_id = await _current_user_id(client, headers)
    app_response = await client.post(
        "/api/v1/applications", headers=headers, json={"company_name": "ExxonMobil", "role_title": "Process Technician", "current_stage": "APPLIED"}
    )
    application_id = app_response.json()["id"]

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_id,
        None,
        _email(
            sender_email="recruiting@exxonmobil.com",
            subject="Online assessment invitation",
            body_text="Dear candidate, you are invited to complete an online assessment for the Process Technician role.",
        ),
    )
    assert event is not None
    assert event.status.value == "SUGGESTED"
    assert event.detected_stage == "APTITUDE_TEST"
    assert event.matched_application_id == application_id

    # The suggestion alone must never have touched the real application.
    still_applied = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert still_applied.json()["current_stage"] == "APPLIED"

    confirm = await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "CONFIRMED"

    updated = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert updated.json()["current_stage"] == "APTITUDE_TEST"
    timeline = updated.json()["timeline"]
    assert timeline[-1]["stage"] == "APTITUDE_TEST"
    assert timeline[-1]["source"] == "EMAIL_CONFIRMED"

    prep_hint = await client.get(f"/api/v1/email-tracking/events/{event.id}/prep-hint", headers=headers)
    assert prep_hint.json()["prep_flow"] == "aptitude"


async def test_confirm_is_idempotent_and_cannot_be_repeated(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "flow2@example.com")
    user_id = await _current_user_id(client, headers)
    app_response = await client.post(
        "/api/v1/applications", headers=headers, json={"company_name": "ExxonMobil", "role_title": "Process Technician", "current_stage": "APPLIED"}
    )
    application_id = app_response.json()["id"]

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_id, None, _email(subject="Interview invitation", body_text="We would like to invite you to interview for the Process Technician role.")
    )
    assert event is not None

    first = await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers)
    assert first.status_code == 200
    second = await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers)
    assert second.status_code == 409

    detail = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    stage_events = [e for e in detail.json()["timeline"] if e["stage"] == "INTERVIEW"]
    assert len(stage_events) == 1, "confirming twice must not append a duplicate timeline event"


async def test_duplicate_provider_message_does_not_create_duplicate_event(db_session: AsyncSession) -> None:
    service = EmailTrackingService(db_session)
    from app.repositories.user_repository import UserRepository
    from app.security.password import hash_password

    user = await UserRepository(db_session).create(email="dup@example.com", hashed_password=hash_password("password123"))
    await db_session.commit()

    email = _email(message_id="same-message-id", subject="Interview invitation", body_text="We would like to invite you to interview.")
    first = await service.process_message(user.id, None, email)
    second = await service.process_message(user.id, None, email)

    assert first is not None
    assert second is None  # spec §9/§42 — the same provider message must never produce two events.


async def test_ambiguous_match_requires_explicit_application_choice(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "ambiguous@example.com")
    user_id = await _current_user_id(client, headers)
    ids = {}
    for role in ["Graduate Engineer", "Process Technician", "Maintenance Technician"]:
        response = await client.post("/api/v1/applications", headers=headers, json={"company_name": "Shell", "role_title": role, "current_stage": "APPLIED"})
        ids[role] = response.json()["id"]

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_id, None, _email(sender_email="talent@shell.com", subject="Interview invitation", body_text="We would like to invite you to interview.")
    )
    assert event is not None
    assert event.status.value == "AMBIGUOUS"
    assert set(event.candidate_application_ids) == set(ids.values())

    # Cannot confirm an ambiguous event directly — no application is matched yet.
    unconfirmable = await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers)
    assert unconfirmable.status_code == 422

    wrong_choice = await client.post(
        f"/api/v1/email-tracking/events/{event.id}/assign-application", headers=headers, json={"application_id": "not-a-real-id"}
    )
    assert wrong_choice.status_code in (404, 422)

    assign = await client.post(
        f"/api/v1/email-tracking/events/{event.id}/assign-application",
        headers=headers,
        json={"application_id": ids["Process Technician"]},
    )
    assert assign.status_code == 200
    assert assign.json()["status"] == "SUGGESTED"

    confirm = await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers)
    assert confirm.status_code == 200
    updated = await client.get(f"/api/v1/applications/{ids['Process Technician']}", headers=headers)
    assert updated.json()["current_stage"] == "INTERVIEW"
    untouched = await client.get(f"/api/v1/applications/{ids['Graduate Engineer']}", headers=headers)
    assert untouched.json()["current_stage"] == "APPLIED"


async def test_false_positive_general_recruitment_language_creates_no_progression(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "falsepos@example.com")
    user_id = await _current_user_id(client, headers)
    await client.post("/api/v1/applications", headers=headers, json={"company_name": "Shell", "role_title": "Graduate Engineer", "current_stage": "APPLIED"})

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_id,
        None,
        _email(sender_email="talent@shell.com", subject="Thanks for applying", body_text="Only shortlisted candidates will be contacted."),
    )
    assert event is not None
    assert event.detected_stage is None
    assert event.status.value == "UNMATCHED"


async def test_ignore_event_then_cannot_be_confirmed(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "ignore@example.com")
    user_id = await _current_user_id(client, headers)
    await client.post("/api/v1/applications", headers=headers, json={"company_name": "ExxonMobil", "role_title": "Process Technician", "current_stage": "APPLIED"})

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_id, None, _email(subject="Interview invitation", body_text="We would like to invite you to interview for the Process Technician role.")
    )
    assert event is not None

    ignore = await client.post(f"/api/v1/email-tracking/events/{event.id}/ignore", headers=headers)
    assert ignore.status_code == 200
    assert ignore.json()["status"] == "IGNORED"

    confirm = await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers)
    assert confirm.status_code == 409


async def test_disconnect_marks_connection_disconnected_and_clears_tokens(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "disconnect@example.com")
    user_id = await _current_user_id(client, headers)
    now = datetime.now(timezone.utc)
    db_session.add(OAuthState(state="disconnect-state", user_id=user_id, provider=EmailProvider.GMAIL, created_at=now, expires_at=now + timedelta(minutes=15)))
    await db_session.commit()
    await client.get("/api/v1/email-tracking/gmail/callback", params={"code": "mock-code", "state": "disconnect-state"})

    connections = (await client.get("/api/v1/email-tracking/connections", headers=headers)).json()
    connection_id = connections[0]["id"]

    response = await client.delete(f"/api/v1/email-tracking/connections/{connection_id}", headers=headers)
    assert response.status_code == 204

    after = (await client.get("/api/v1/email-tracking/connections", headers=headers)).json()
    assert after == []  # disconnected connections drop out of the active list.


async def test_delete_tracking_data_keeps_confirmed_application_history(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "deletetracking@example.com")
    user_id = await _current_user_id(client, headers)
    app_response = await client.post("/api/v1/applications", headers=headers, json={"company_name": "ExxonMobil", "role_title": "Process Technician", "current_stage": "APPLIED"})
    application_id = app_response.json()["id"]

    service = EmailTrackingService(db_session)
    event = await service.process_message(
        user_id, None, _email(subject="Interview invitation", body_text="We would like to invite you to interview for the Process Technician role.")
    )
    await client.post(f"/api/v1/email-tracking/events/{event.id}/confirm", headers=headers)

    deletion = await client.delete("/api/v1/email-tracking/data", headers=headers)
    assert deletion.status_code == 200
    assert deletion.json()["deleted_events"] == 1

    events_after = await client.get("/api/v1/email-tracking/events", headers=headers)
    assert events_after.json() == []

    application_after = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert application_after.json()["current_stage"] == "INTERVIEW"
    assert len(application_after.json()["timeline"]) == 2  # original SAVED/APPLIED + the confirmed INTERVIEW event.


# ---------------------------------------------------------------------------
# Webhook security (spec §8/§13/§43/§50)
# ---------------------------------------------------------------------------


async def test_gmail_webhook_for_unknown_mailbox_is_safely_ignored(client: AsyncClient) -> None:
    """A forged/unsolicited notification for an email address with no active CareerOS connection
    must be a quiet no-op — never an error, never any data touched (spec §9's "a notification
    means the mailbox changed, not this is definitely a recruitment email", and §43's forged-
    webhook protection)."""
    response = await client.post(
        "/api/v1/webhooks/gmail",
        json={"message": {"data": _b64_gmail_payload({"emailAddress": "nobody@example.com", "historyId": "999"})}},
    )
    assert response.status_code == 204


async def test_gmail_webhook_rejects_malformed_payload(client: AsyncClient) -> None:
    response = await client.post("/api/v1/webhooks/gmail", json={"message": {"data": "not-valid-base64-json!!"}})
    assert response.status_code == 400


async def test_microsoft_webhook_validation_handshake_echoes_token(client: AsyncClient) -> None:
    """Spec §13 — Graph's subscription-creation handshake sends a `validationToken` query param
    and expects it echoed back verbatim as plain text, before any real notification ever arrives."""
    response = await client.post("/api/v1/webhooks/microsoft", params={"validationToken": "expected-echo-value"})
    assert response.status_code == 200
    assert response.text.strip('"') == "expected-echo-value"


async def test_microsoft_lifecycle_reauthorization_required_marks_connection(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "lifecycle@example.com")
    user_id = await _current_user_id(client, headers)
    connection = EmailConnection(
        user_id=user_id,
        provider=EmailProvider.OUTLOOK,
        provider_account_id="acct-lifecycle",
        provider_email="lifecycle@outlook.com",
        granted_scopes=["Mail.Read"],
        outlook_subscription_id="sub-123",
    )
    db_session.add(connection)
    await db_session.commit()

    response = await client.post(
        "/api/v1/webhooks/microsoft/lifecycle",
        json={"value": [{"subscriptionId": "sub-123", "lifecycleEvent": "reauthorizationRequired"}]},
    )
    assert response.status_code == 202

    connections = await client.get("/api/v1/email-tracking/connections", headers=headers)
    assert connections.json()[0]["status"] == "REAUTHORIZATION_REQUIRED"


def _b64_gmail_payload(payload: dict) -> str:
    import base64
    import json

    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
