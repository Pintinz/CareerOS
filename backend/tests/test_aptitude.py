from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models.question import Question, QuestionCategory, QuestionDifficulty, QuestionOption, QuestionTopic, QuestionType
from app.models.test_session import TestSession
from app.models.user import SubscriptionTier, User
from tests.test_jobs import _create_company, _job_payload, _user_headers

pytestmark = pytest.mark.asyncio


async def _create_category(db_session: AsyncSession, slug: str, name: str | None = None) -> QuestionCategory:
    category = QuestionCategory(name=name or slug, slug=slug)
    db_session.add(category)
    await db_session.flush()
    return category


async def _create_topic(
    db_session: AsyncSession,
    category: QuestionCategory,
    slug: str,
    *,
    name: str | None = None,
    field: str | None = None,
    industry: str | None = None,
) -> QuestionTopic:
    topic = QuestionTopic(category_id=category.id, name=name or slug, slug=slug, field=field, industry=industry)
    db_session.add(topic)
    await db_session.flush()
    return topic


async def _create_question(
    db_session: AsyncSession,
    category: QuestionCategory,
    *,
    topic: QuestionTopic | None = None,
    difficulty: QuestionDifficulty = QuestionDifficulty.EASY,
    options: list[tuple[str, bool]] | None = None,
    marks: float = 1.0,
    negative_marks: float = 0.5,
    qtype: QuestionType = QuestionType.SINGLE_CHOICE,
    text: str = "Sample question?",
) -> Question:
    question = Question(
        question_text=text,
        question_type=qtype,
        category_id=category.id,
        topic_id=topic.id if topic else None,
        field=topic.field if topic else None,
        industry=topic.industry if topic else None,
        difficulty=difficulty,
        explanation="Because the correct option satisfies the stated condition.",
        marks=marks,
        negative_marks=negative_marks,
        is_active=True,
        is_demo=True,
    )
    db_session.add(question)
    await db_session.flush()
    for order, (option_text, is_correct) in enumerate(options or []):
        db_session.add(
            QuestionOption(question_id=question.id, option_text=option_text, is_correct=is_correct, display_order=order)
        )
    await db_session.flush()
    return question


async def _seed_numerical_bank(db_session: AsyncSession, count: int = 5) -> QuestionCategory:
    category = await _create_category(db_session, "numerical-test", "Numerical")
    for i in range(count):
        await _create_question(
            db_session,
            category,
            options=[("Correct", True), ("Wrong A", False), ("Wrong B", False), ("Wrong C", False)],
            text=f"Numerical question {i}?",
        )
    await db_session.commit()
    return category


async def _create_session(client: AsyncClient, headers: dict, **overrides) -> dict:
    payload = {"sections": ["numerical-test"], "difficulty": "EASY", "question_count": 5, "timing": "UNTIMED"}
    payload.update(overrides)
    response = await client.post("/api/v1/aptitude/sessions", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Session creation / generation
# ---------------------------------------------------------------------------


async def test_create_session_hides_correct_answers(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_numerical_bank(db_session, count=5)
    headers = await _user_headers(client)

    session = await _create_session(client, headers)
    assert session["question_count"] == 5
    assert session["status"] == "IN_PROGRESS"
    for question in session["questions"]:
        for option in question["options"]:
            assert "is_correct" not in option


async def test_generation_returns_best_available_set_without_duplicates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session, count=3)
    headers = await _user_headers(client)

    session = await _create_session(client, headers, question_count=10)
    ids = [q["id"] for q in session["questions"]]
    assert len(ids) == 3
    assert len(set(ids)) == 3


async def test_create_session_422_when_no_questions_match(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client)
    response = await client.post(
        "/api/v1/aptitude/sessions",
        headers=headers,
        json={"sections": ["nonexistent-section"], "difficulty": "EASY", "question_count": 5, "timing": "UNTIMED"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Isolation (404-not-403 pattern)
# ---------------------------------------------------------------------------


async def test_session_is_isolated_per_user(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_numerical_bank(db_session)
    headers_a = await _user_headers(client, "a@example.com")
    headers_b = await _user_headers(client, "b@example.com")

    session = await _create_session(client, headers_a)

    get_as_b = await client.get(f"/api/v1/aptitude/sessions/{session['id']}", headers=headers_b)
    assert get_as_b.status_code == 404

    submit_as_b = await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers_b)
    assert submit_as_b.status_code == 404


# ---------------------------------------------------------------------------
# Answering / flagging
# ---------------------------------------------------------------------------


async def test_answer_can_be_set_and_changed_before_submit(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client)
    session = await _create_session(client, headers)
    question = session["questions"][0]
    correct_option = next(o for o in question["options"] if o["option_text"] == "Correct")
    wrong_option = next(o for o in question["options"] if o["option_text"] == "Wrong A")

    resp = await client.put(
        f"/api/v1/aptitude/sessions/{session['id']}/answers/{question['id']}",
        headers=headers,
        json={"selected_option_ids": [wrong_option["id"]]},
    )
    assert resp.status_code == 200
    assert resp.json()["answer_state"]["selected_option_ids"] == [wrong_option["id"]]

    resp2 = await client.put(
        f"/api/v1/aptitude/sessions/{session['id']}/answers/{question['id']}",
        headers=headers,
        json={"selected_option_ids": [correct_option["id"]]},
    )
    assert resp2.json()["answer_state"]["selected_option_ids"] == [correct_option["id"]]


async def test_flag_toggles(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client)
    session = await _create_session(client, headers)
    question_id = session["questions"][0]["id"]

    first = await client.post(f"/api/v1/aptitude/sessions/{session['id']}/flag/{question_id}", headers=headers)
    assert first.json()["answer_state"]["is_flagged"] is True

    second = await client.post(f"/api/v1/aptitude/sessions/{session['id']}/flag/{question_id}", headers=headers)
    assert second.json()["answer_state"]["is_flagged"] is False


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


async def test_submit_grades_with_negative_marking_and_unanswered(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session, count=4)
    headers = await _user_headers(client)
    session = await _create_session(client, headers, question_count=4)
    questions = session["questions"]

    def option(q: dict, text: str) -> str:
        return next(o["id"] for o in q["options"] if o["option_text"] == text)

    # Q0 correct, Q1 incorrect, Q2 unanswered, Q3 correct.
    await client.put(
        f"/api/v1/aptitude/sessions/{session['id']}/answers/{questions[0]['id']}",
        headers=headers, json={"selected_option_ids": [option(questions[0], "Correct")]},
    )
    await client.put(
        f"/api/v1/aptitude/sessions/{session['id']}/answers/{questions[1]['id']}",
        headers=headers, json={"selected_option_ids": [option(questions[1], "Wrong A")]},
    )
    await client.put(
        f"/api/v1/aptitude/sessions/{session['id']}/answers/{questions[3]['id']}",
        headers=headers, json={"selected_option_ids": [option(questions[3], "Correct")]},
    )

    result = await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["correct_count"] == 2
    assert body["incorrect_count"] == 1
    assert body["unanswered_count"] == 1
    # marks=1.0, negative_marks=0.5: 1 + (-0.5) + 0 + 1 = 1.5 out of 4 -> 37.5%
    assert body["score"] == 1.5
    assert body["total_marks"] == 4
    assert abs(body["percentage"] - 37.5) < 1e-6
    assert body["performance_label"] == "Needs Improvement"


async def test_cannot_modify_answers_or_resubmit_after_submission(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client)
    session = await _create_session(client, headers)
    question_id = session["questions"][0]["id"]

    submit = await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers)
    assert submit.status_code == 200

    blocked = await client.put(
        f"/api/v1/aptitude/sessions/{session['id']}/answers/{question_id}",
        headers=headers, json={"selected_option_ids": []},
    )
    assert blocked.status_code == 409

    blocked_flag = await client.post(f"/api/v1/aptitude/sessions/{session['id']}/flag/{question_id}", headers=headers)
    assert blocked_flag.status_code == 409

    # Submitting again is idempotent, not an error — it just returns the already-graded result.
    resubmit = await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers)
    assert resubmit.status_code == 200
    assert resubmit.json()["score"] == submit.json()["score"]


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


async def test_review_hidden_before_submit_and_reveals_answers_after(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client)
    session = await _create_session(client, headers)

    before = await client.get(f"/api/v1/aptitude/sessions/{session['id']}/review", headers=headers)
    assert before.status_code == 409

    await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers)

    after = await client.get(f"/api/v1/aptitude/sessions/{session['id']}/review", headers=headers)
    assert after.status_code == 200
    review_question = after.json()["questions"][0]
    correct_options = [o for o in review_question["options"] if o["is_correct"]]
    assert len(correct_options) == 1
    assert correct_options[0]["option_text"] == "Correct"


# ---------------------------------------------------------------------------
# Timer authority / auto-submit
# ---------------------------------------------------------------------------


async def test_expired_session_auto_submits_on_access_and_rejects_further_answers(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client)
    session = await _create_session(
        client, headers, timing="OVERALL", time_limit_minutes=10, question_count=5
    )
    question_id = session["questions"][0]["id"]

    # Simulate the timer having expired by directly backdating expires_at in the database —
    # the backend must independently notice this on the next access, not trust a client timer.
    db_row = await db_session.get(TestSession, session["id"])
    db_row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    await db_session.commit()

    detail = await client.get(f"/api/v1/aptitude/sessions/{session['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "AUTO_SUBMITTED"
    assert detail.json()["remaining_seconds"] is None

    blocked = await client.put(
        f"/api/v1/aptitude/sessions/{session['id']}/answers/{question_id}",
        headers=headers, json={"selected_option_ids": []},
    )
    assert blocked.status_code == 409

    result = await client.get(f"/api/v1/aptitude/sessions/{session['id']}/results", headers=headers)
    assert result.status_code == 200
    assert result.json()["auto_submitted"] is True


async def test_timed_session_reports_remaining_seconds_while_untimed_does_not(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    # Two different users (Phase 11 §64: the free tier now allows only 1 aptitude session/day per
    # user server-side — using separate users here isolates this test from that limit entirely,
    # since it's testing timed-vs-untimed session shape, not per-user daily quota behavior).
    timed_headers = await _user_headers(client, "timed-session@example.com")
    untimed_headers = await _user_headers(client, "untimed-session@example.com")

    timed = await _create_session(client, timed_headers, timing="OVERALL", time_limit_minutes=10)
    assert timed["remaining_seconds"] is not None
    assert 0 < timed["remaining_seconds"] <= 600

    untimed = await _create_session(client, untimed_headers, timing="UNTIMED")
    assert untimed["remaining_seconds"] is None
    assert untimed["expires_at"] is None


async def test_review_is_isolated_per_user_even_after_submission(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    headers_a = await _user_headers(client, "reviewer-a@example.com")
    headers_b = await _user_headers(client, "reviewer-b@example.com")

    session = await _create_session(client, headers_a)
    await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers_a)

    blocked = await client.get(f"/api/v1/aptitude/sessions/{session['id']}/review", headers=headers_b)
    assert blocked.status_code == 404


# ---------------------------------------------------------------------------
# Analytics / recommendations
# ---------------------------------------------------------------------------


async def test_analytics_and_weak_topic_recommendation_require_minimum_attempts(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await _create_category(db_session, "technical-test", "Technical")
    weak_topic = await _create_topic(db_session, category, "weak-topic-test", name="Weak Topic")
    borderline_topic = await _create_topic(db_session, category, "borderline-topic-test", name="Borderline Topic")

    # Three separate single-question questions under the weak topic, each answered incorrectly
    # across three separate sessions -> attempted=3, accuracy=0% (below the weak-topic threshold).
    for i in range(3):
        await _create_question(
            db_session, category, topic=weak_topic,
            options=[("Correct", True), ("Wrong", False)], text=f"Weak topic question {i}?",
        )
    # Two questions under the borderline topic, also always wrong, but only 2 attempts total —
    # below MIN_ATTEMPTS_FOR_TOPIC_RECOMMENDATION, so it must not appear even though accuracy is low.
    for i in range(2):
        await _create_question(
            db_session, category, topic=borderline_topic,
            options=[("Correct", True), ("Wrong", False)], text=f"Borderline topic question {i}?",
        )
    await db_session.commit()

    headers = await _user_headers(client)
    # This test needs 3 sessions in one day for one user, above the default free-tier limit of 1
    # (Phase 11 §64 server-side enforcement) — mark them PRO here since the test's actual point is
    # analytics aggregation across sessions, not free-tier gating.
    user_result = await db_session.execute(select(User).where(User.email == "candidate@example.com"))
    user_result.scalar_one().subscription_tier = SubscriptionTier.PRO
    await db_session.commit()

    for _ in range(3):
        session = await _create_session(
            client, headers, sections=["technical-test"], question_count=1
        )
        # Answer whichever single question came back with the wrong option, whichever topic it's from.
        question = session["questions"][0]
        wrong = next(o for o in question["options"] if o["option_text"] == "Wrong")
        await client.put(
            f"/api/v1/aptitude/sessions/{session['id']}/answers/{question['id']}",
            headers=headers, json={"selected_option_ids": [wrong["id"]]},
        )
        await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers)

    analytics = await client.get("/api/v1/aptitude/analytics", headers=headers)
    assert analytics.status_code == 200
    assert analytics.json()["tests_completed"] == 3

    recommendations = await client.get("/api/v1/aptitude/recommendations", headers=headers)
    assert recommendations.status_code == 200
    weak_names = {t["topic_name"] for t in recommendations.json()["weak_topics"]}
    assert "Borderline Topic" not in weak_names, (analytics.json()["by_topic"], recommendations.json())


# ---------------------------------------------------------------------------
# Job-specific generation / application linkage
# ---------------------------------------------------------------------------


async def test_job_specific_session_prefers_mapped_technical_topics(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await _create_category(db_session, "technical-job-test", "Technical")
    pumps_topic = await _create_topic(db_session, category, "pumps", name="Pumps")
    other_topic = await _create_topic(db_session, category, "other-technical-test", name="Other")

    for i in range(2):
        await _create_question(
            db_session, category, topic=pumps_topic,
            options=[("Correct", True), ("Wrong", False)], text=f"Pumps question {i}?",
        )
    for i in range(5):
        await _create_question(
            db_session, category, topic=other_topic,
            options=[("Correct", True), ("Wrong", False)], text=f"Other question {i}?",
        )
    await db_session.commit()

    headers = await _user_headers(client)

    # Session creation only accepts job_id/application_id for context, not a raw job_role field,
    # so route the "Process Technician" keyword through a real job record.
    admin_headers = await _register_admin_and_login(client, db_session)
    company_id = await _create_company(client, admin_headers, name="Demo Oil Co")
    job_response = await client.post(
        "/api/v1/admin/jobs",
        headers=admin_headers,
        json=_job_payload(company_id, title="Process Technician", industry="Oil & Gas"),
    )
    job_id = job_response.json()["id"]

    session = await _create_session(
        client, headers, sections=["technical-job-test"], question_count=2, job_id=job_id
    )
    topic_names = {q["topic_name"] for q in session["questions"]}
    assert topic_names == {"Pumps"}


async def test_practice_weak_areas_topic_slug_override_restricts_generation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await _create_category(db_session, "logical-topic-slug-test", "Logical")
    weak_topic = await _create_topic(db_session, category, "weak-slug-test", name="Weak Slug Topic")
    other_topic = await _create_topic(db_session, category, "other-slug-test", name="Other Slug Topic")
    for i in range(2):
        await _create_question(
            db_session, category, topic=weak_topic,
            options=[("Correct", True), ("Wrong", False)], text=f"Weak slug question {i}?",
        )
    for i in range(5):
        await _create_question(
            db_session, category, topic=other_topic,
            options=[("Correct", True), ("Wrong", False)], text=f"Other slug question {i}?",
        )
    await db_session.commit()

    headers = await _user_headers(client)
    response = await client.post(
        "/api/v1/aptitude/sessions",
        headers=headers,
        json={
            "sections": [],
            "difficulty": "EASY",
            "question_count": 2,
            "timing": "UNTIMED",
            "topic_slugs": ["weak-slug-test"],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert {q["topic_name"] for q in body["questions"]} == {"Weak Slug Topic"}
    assert all(q["topic_slug"] == "weak-slug-test" for q in body["questions"])


async def test_application_linked_session_does_not_mutate_application_stage(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client)

    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company_name": "Acme Corp", "role_title": "Process Technician", "current_stage": "APTITUDE_TEST"},
    )
    application_id = application.json()["id"]

    session = await _create_session(client, headers, application_id=application_id)
    assert session["application_id"] == application_id

    await client.post(f"/api/v1/aptitude/sessions/{session['id']}/submit", headers=headers)

    detail = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert detail.json()["current_stage"] == "APTITUDE_TEST"


async def test_admin_question_bank_crud(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_headers = await _register_admin_and_login(client, db_session)

    category_response = await client.post(
        "/api/v1/admin/aptitude/categories", headers=admin_headers,
        json={"name": "Numerical Reasoning", "slug": "numerical-admin-test"},
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    topic_response = await client.post(
        "/api/v1/admin/aptitude/topics", headers=admin_headers,
        json={"category_id": category_id, "name": "Percentages", "slug": "percentages-admin-test"},
    )
    assert topic_response.status_code == 201
    topic_id = topic_response.json()["id"]

    create_response = await client.post(
        "/api/v1/admin/aptitude/questions",
        headers=admin_headers,
        json={
            "question_text": "What is 10% of 50?",
            "question_type": "SINGLE_CHOICE",
            "category_id": category_id,
            "topic_id": topic_id,
            "difficulty": "EASY",
            "explanation": "10% of 50 is 5.",
            "options": [
                {"option_text": "5", "is_correct": True, "display_order": 0},
                {"option_text": "10", "is_correct": False, "display_order": 1},
            ],
        },
    )
    assert create_response.status_code == 201, create_response.text
    question_id = create_response.json()["id"]
    assert len(create_response.json()["options"]) == 2

    # Never exposed to a normal (non-admin) user.
    user_headers = await _user_headers(client, "not-an-admin@example.com")
    forbidden = await client.get("/api/v1/admin/aptitude/questions", headers=user_headers)
    assert forbidden.status_code in (401, 403)

    update_response = await client.put(
        f"/api/v1/admin/aptitude/questions/{question_id}", headers=admin_headers,
        json={"explanation": "Updated explanation."},
    )
    assert update_response.status_code == 200
    assert update_response.json()["explanation"] == "Updated explanation."

    list_response = await client.get(
        "/api/v1/admin/aptitude/questions", headers=admin_headers, params={"category_id": category_id}
    )
    assert list_response.json()["total"] == 1

    delete_response = await client.delete(f"/api/v1/admin/aptitude/questions/{question_id}", headers=admin_headers)
    assert delete_response.status_code == 204


async def _register_admin_and_login(client: AsyncClient, db_session: AsyncSession) -> dict:
    from app.models.admin_user import AdminRole
    from app.repositories.admin_user_repository import AdminUserRepository
    from app.security.password import hash_password

    repo = AdminUserRepository(db_session)
    await repo.create(email="apt-admin@example.com", hashed_password=hash_password("adminpass1"), role=AdminRole.ADMIN)
    await db_session.commit()
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "apt-admin@example.com", "password": "adminpass1"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_timed_session_timestamps_carry_utc_offset_after_reload(client: AsyncClient, db_session: AsyncSession) -> None:
    """Regression: SQLite returns naive datetimes, which were serialized without an offset, so an app in
    Lagos (UTC+1) read expires_at an hour early and auto-submitted a fresh 30-minute test."""
    from datetime import datetime

    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client)
    session = await _create_session(client, headers, timing="OVERALL", time_limit_minutes=30)
    db_session.expunge_all()  # force the next read to load from the database

    reloaded = (await client.get(f"/api/v1/aptitude/sessions/{session['id']}", headers=headers)).json()
    expires_at, server_time = datetime.fromisoformat(reloaded["expires_at"]), datetime.fromisoformat(reloaded["server_time"])
    assert expires_at.tzinfo is not None and server_time.tzinfo is not None
    assert 29 * 60 <= (expires_at - server_time).total_seconds() <= 30 * 60
    assert 29 * 60 <= reloaded["remaining_seconds"] <= 30 * 60
    assert reloaded["status"] == "IN_PROGRESS"
