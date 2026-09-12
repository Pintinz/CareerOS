import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import (
    InterviewDifficulty,
    InterviewQuestion,
    InterviewQuestionCategory,
    InterviewTopic,
    StarCategory,
)
from tests.test_jobs import _create_company, _job_payload, _user_headers

pytestmark = pytest.mark.asyncio


async def _create_category(db_session: AsyncSession, slug: str, name: str | None = None) -> InterviewQuestionCategory:
    category = InterviewQuestionCategory(name=name or slug, slug=slug)
    db_session.add(category)
    await db_session.flush()
    return category


async def _create_topic(
    db_session: AsyncSession, category: InterviewQuestionCategory, slug: str, *, name: str | None = None,
    field: str | None = None, industry: str | None = None,
) -> InterviewTopic:
    topic = InterviewTopic(category_id=category.id, name=name or slug, slug=slug, field=field, industry=industry)
    db_session.add(topic)
    await db_session.flush()
    return topic


async def _create_question(
    db_session: AsyncSession, category: InterviewQuestionCategory, *, topic: InterviewTopic | None = None,
    difficulty: InterviewDifficulty = InterviewDifficulty.EASY, company_id: str | None = None,
    star_tags: list[str] | None = None, text: str = "Sample interview question?",
) -> InterviewQuestion:
    question = InterviewQuestion(
        question_text=text,
        category_id=category.id,
        topic_id=topic.id if topic else None,
        field=topic.field if topic else None,
        industry=topic.industry if topic else None,
        company_id=company_id,
        difficulty=difficulty,
        answer_guidance={"assessing": "test", "strong_answer_includes": ["a"], "common_mistakes": [], "technical_concepts": []},
        evaluation_points=["a"],
        star_tags=star_tags or [],
        is_active=True,
        is_demo=True,
    )
    db_session.add(question)
    await db_session.flush()
    return question


async def _seed_bank(db_session: AsyncSession, count: int = 5) -> InterviewQuestionCategory:
    category = await _create_category(db_session, "behavioral-test", "Behavioral")
    for i in range(count):
        await _create_question(db_session, category, text=f"Behavioral question {i}?")
    await db_session.commit()
    return category


async def _create_session(client: AsyncClient, headers: dict, **overrides) -> dict:
    payload = {"categories": ["behavioral-test"], "difficulty": "EASY", "question_count": 5}
    payload.update(overrides)
    response = await client.post("/api/v1/interview/sessions", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------


async def test_create_session_generates_requested_question_count(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_bank(db_session, count=5)
    headers = await _user_headers(client)
    session = await _create_session(client, headers)
    assert session["question_count"] == 5
    assert session["status"] == "IN_PROGRESS"
    assert len(session["questions"]) == 5


async def test_generation_returns_best_available_set_without_duplicates(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_bank(db_session, count=3)
    headers = await _user_headers(client)
    session = await _create_session(client, headers, question_count=10)
    ids = [q["id"] for q in session["questions"]]
    assert len(ids) == 3
    assert len(set(ids)) == 3


async def test_create_session_422_when_no_questions_match(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client)
    response = await client.post(
        "/api/v1/interview/sessions", headers=headers,
        json={"categories": ["nonexistent"], "difficulty": "EASY", "question_count": 5},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


async def test_session_is_isolated_per_user(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_bank(db_session)
    headers_a = await _user_headers(client, "int-a@example.com")
    headers_b = await _user_headers(client, "int-b@example.com")
    session = await _create_session(client, headers_a)

    get_as_b = await client.get(f"/api/v1/interview/sessions/{session['id']}", headers=headers_b)
    assert get_as_b.status_code == 404

    complete_as_b = await client.post(f"/api/v1/interview/sessions/{session['id']}/complete", headers=headers_b)
    assert complete_as_b.status_code == 404


# ---------------------------------------------------------------------------
# Answering / completion
# ---------------------------------------------------------------------------


async def test_answering_and_completion_computes_stats(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_bank(db_session, count=4)
    headers = await _user_headers(client)
    session = await _create_session(client, headers, question_count=4)
    questions = session["questions"]

    await client.put(
        f"/api/v1/interview/sessions/{session['id']}/answers/{questions[0]['id']}",
        headers=headers, json={"answer_text": "A fairly detailed answer describing what I did in that situation.", "self_rating": 4, "used_star": True},
    )
    await client.put(
        f"/api/v1/interview/sessions/{session['id']}/answers/{questions[1]['id']}",
        headers=headers, json={"is_marked_practiced": True},
    )
    await client.put(
        f"/api/v1/interview/sessions/{session['id']}/answers/{questions[2]['id']}",
        headers=headers, json={"is_skipped": True},
    )
    # questions[3] left untouched entirely.

    result = await client.post(f"/api/v1/interview/sessions/{session['id']}/complete", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["questions_completed"] == 2
    assert body["questions_skipped"] == 1
    assert body["average_self_rating"] == 4.0


async def test_cannot_modify_answers_after_completion(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_bank(db_session)
    headers = await _user_headers(client)
    session = await _create_session(client, headers)
    question_id = session["questions"][0]["id"]

    complete = await client.post(f"/api/v1/interview/sessions/{session['id']}/complete", headers=headers)
    assert complete.status_code == 200

    blocked = await client.put(
        f"/api/v1/interview/sessions/{session['id']}/answers/{question_id}", headers=headers, json={"answer_text": "too late"}
    )
    assert blocked.status_code == 409

    # Completing again is idempotent.
    again = await client.post(f"/api/v1/interview/sessions/{session['id']}/complete", headers=headers)
    assert again.status_code == 200


# ---------------------------------------------------------------------------
# Company-specific / job-specific filtering
# ---------------------------------------------------------------------------


async def test_company_specific_generation_prefers_tagged_questions(client: AsyncClient, db_session: AsyncSession) -> None:
    category = await _create_category(db_session, "company-test", "Company-Specific")
    admin_headers = await _register_admin_and_login(client, db_session)
    company_id = await _create_company(client, admin_headers, name="Demo Target Co")

    for i in range(2):
        await _create_question(db_session, category, company_id=company_id, text=f"Tagged question {i}?")
    for i in range(5):
        await _create_question(db_session, category, text=f"Untagged question {i}?")
    await db_session.commit()

    headers = await _user_headers(client, "company-pref@example.com")
    session = await _create_session(
        client, headers, categories=["company-test"], question_count=2, company_id=company_id
    )
    assert len(session["questions"]) == 2
    assert all(q["question_text"].startswith("Tagged question") for q in session["questions"])


async def test_job_specific_generation_prefers_mapped_topics(client: AsyncClient, db_session: AsyncSession) -> None:
    category = await _create_category(db_session, "technical-job-test", "Technical")
    pumps_topic = await _create_topic(db_session, category, "pumps", name="Pumps")
    other_topic = await _create_topic(db_session, category, "other-int-test", name="Other")

    for i in range(2):
        await _create_question(db_session, category, topic=pumps_topic, text=f"Pumps question {i}?")
    for i in range(5):
        await _create_question(db_session, category, topic=other_topic, text=f"Other question {i}?")
    await db_session.commit()

    headers = await _user_headers(client, "job-pref@example.com")
    admin_headers = await _register_admin_and_login(client, db_session, email="job-pref-admin@example.com")
    company_id = await _create_company(client, admin_headers, name="Demo Oil Co 2")
    job_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers,
        json=_job_payload(company_id, title="Process Technician", industry="Oil & Gas"),
    )
    job_id = job_response.json()["id"]

    session = await _create_session(client, headers, categories=["technical-job-test"], question_count=2, job_id=job_id)
    assert all(q["topic_name"] == "Pumps" for q in session["questions"])


# ---------------------------------------------------------------------------
# Application-linked generation / no stage mutation
# ---------------------------------------------------------------------------


async def test_application_linked_session_resolves_job_and_does_not_mutate_stage(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_bank(db_session)
    headers = await _user_headers(client, "app-linked@example.com")
    admin_headers = await _register_admin_and_login(client, db_session, email="app-linked-admin@example.com")
    company_id = await _create_company(client, admin_headers, name="Demo Linked Co")
    job_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers, json=_job_payload(company_id, title="Process Technician")
    )
    await client.put(f"/api/v1/admin/jobs/{job_response.json()['id']}", headers=admin_headers, json={"status": "PUBLISHED"})
    job_id = job_response.json()["id"]

    application = await client.post(
        "/api/v1/applications", headers=headers,
        json={"job_id": job_id, "current_stage": "INTERVIEW"},
    )
    application_id = application.json()["id"]

    session = await _create_session(client, headers, application_id=application_id, categories=["behavioral-test"])
    assert session["application_id"] == application_id
    assert session["job_id"] == job_id
    assert session["company_id"] == company_id

    await client.post(f"/api/v1/interview/sessions/{session['id']}/complete", headers=headers)

    detail = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert detail.json()["current_stage"] == "INTERVIEW"


# ---------------------------------------------------------------------------
# Analytics / readiness
# ---------------------------------------------------------------------------


async def test_readiness_shows_insufficient_data_then_a_real_score(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_bank(db_session, count=5)
    headers = await _user_headers(client, "readiness@example.com")

    empty_readiness = await client.get("/api/v1/interview/readiness", headers=headers)
    assert empty_readiness.status_code == 200
    assert empty_readiness.json()["insufficient_data"] is True
    assert empty_readiness.json()["overall"] is None

    session = await _create_session(client, headers, question_count=5)
    for question in session["questions"]:
        await client.put(
            f"/api/v1/interview/sessions/{session['id']}/answers/{question['id']}",
            headers=headers, json={"is_marked_practiced": True},
        )
    await client.post(f"/api/v1/interview/sessions/{session['id']}/complete", headers=headers)

    real_readiness = await client.get("/api/v1/interview/readiness", headers=headers)
    assert real_readiness.json()["insufficient_data"] is False
    assert real_readiness.json()["overall"] is not None
    assert 0 <= real_readiness.json()["overall"] <= 100


async def test_analytics_reflects_completed_session_activity(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_bank(db_session, count=3)
    headers = await _user_headers(client, "analytics@example.com")
    session = await _create_session(client, headers, question_count=3)
    for question in session["questions"]:
        await client.put(
            f"/api/v1/interview/sessions/{session['id']}/answers/{question['id']}",
            headers=headers, json={"is_marked_practiced": True, "self_rating": 3},
        )
    await client.post(f"/api/v1/interview/sessions/{session['id']}/complete", headers=headers)

    analytics = await client.get("/api/v1/interview/analytics", headers=headers)
    assert analytics.status_code == 200
    body = analytics.json()
    assert body["sessions_completed"] == 1
    assert body["questions_practiced"] == 3
    assert body["average_self_rating"] == 3.0


# ---------------------------------------------------------------------------
# STAR stories
# ---------------------------------------------------------------------------


async def test_star_story_crud_and_isolation(client: AsyncClient, db_session: AsyncSession) -> None:
    headers_a = await _user_headers(client, "star-a@example.com")
    headers_b = await _user_headers(client, "star-b@example.com")

    create = await client.post(
        "/api/v1/star-stories", headers=headers_a,
        json={"title": "Pump failure recovery", "category": "EQUIPMENT_FAILURE", "situation": "s", "task": "t", "action": "a", "result": "r"},
    )
    assert create.status_code == 201
    story_id = create.json()["id"]

    get_as_b = await client.get(f"/api/v1/star-stories/{story_id}", headers=headers_b)
    assert get_as_b.status_code == 404

    update = await client.put(f"/api/v1/star-stories/{story_id}", headers=headers_a, json={"title": "Updated title"})
    assert update.status_code == 200
    assert update.json()["title"] == "Updated title"

    delete = await client.delete(f"/api/v1/star-stories/{story_id}", headers=headers_a)
    assert delete.status_code == 204

    listing = await client.get("/api/v1/star-stories", headers=headers_a)
    assert listing.json() == []


async def test_star_completeness_check_reports_concrete_gaps(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "star-complete@example.com")

    incomplete = await client.post(
        "/api/v1/star-stories", headers=headers,
        json={
            "title": "Missing result",
            "category": "SAFETY",
            "situation": "There was a hazardous gas leak detected during routine inspection of the unit.",
            "task": "I needed to isolate the source and evacuate nearby personnel immediately.",
            "action": "I",
            "result": None,
        },
    )
    assert incomplete.status_code == 201
    completeness = incomplete.json()["completeness"]
    assert completeness["is_complete"] is False
    assert "no_result" in completeness["gaps"]
    assert "very_short_action" in completeness["gaps"]

    complete = await client.post(
        "/api/v1/star-stories", headers=headers,
        json={
            "title": "Well-formed story",
            "category": "PROBLEM_SOLVING",
            "situation": "Production output had dropped 15% over two weeks with no obvious cause identified by the team.",
            "task": "As the lead technician I was responsible for diagnosing the root cause within one week.",
            "action": "I reviewed historical trend data, isolated three candidate causes, and tested each systematically.",
            "result": "I identified a failing sensor and replaced it, restoring output to 100% within 3 days.",
        },
    )
    assert complete.json()["completeness"]["is_complete"] is True


async def test_question_to_star_matching_suggests_relevant_stories(client: AsyncClient, db_session: AsyncSession) -> None:
    category = await _create_category(db_session, "behavioral-star-test", "Behavioral")
    await _create_question(
        db_session, category, star_tags=["equipment_failure", "problem_solving"],
        text="Tell me about a time you solved a difficult problem.",
    )
    await db_session.commit()

    headers = await _user_headers(client, "star-match@example.com")
    story = await client.post(
        "/api/v1/star-stories", headers=headers,
        json={"title": "Fixed a failing pump", "category": "EQUIPMENT_FAILURE", "situation": "s", "task": "t", "action": "a", "result": "r"},
    )
    story_id = story.json()["id"]

    session = await _create_session(client, headers, categories=["behavioral-star-test"], question_count=1)
    assert session["questions"][0]["suggested_star_story_ids"] == [story_id]


async def test_preparation_progress_checklist_and_topic_review(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "progress@example.com")

    initial = await client.get("/api/v1/interview/prep/progress", headers=headers)
    assert initial.status_code == 200
    assert all(item["is_done"] is False for item in initial.json()["checklist"])

    updated = await client.put(
        "/api/v1/interview/prep/checklist", headers=headers, json={"key": "understand_business", "is_done": True}
    )
    assert updated.status_code == 200
    done_item = next(i for i in updated.json()["checklist"] if i["key"] == "understand_business")
    assert done_item["is_done"] is True

    topic_review = await client.put(
        "/api/v1/interview/prep/topics", headers=headers, json={"topic_slug": "pumps", "is_reviewed": True}
    )
    assert "pumps" in topic_review.json()["reviewed_topics"]


async def test_admin_interview_question_bank_crud(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_headers = await _register_admin_and_login(client, db_session, email="crud-admin@example.com")

    category_response = await client.post(
        "/api/v1/admin/interview/categories", headers=admin_headers, json={"name": "HR / General", "slug": "hr-admin-test"}
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    create_response = await client.post(
        "/api/v1/admin/interview/questions", headers=admin_headers,
        json={
            "question_text": "Tell me about yourself.",
            "category_id": category_id,
            "difficulty": "EASY",
            "answer_guidance": {"assessing": "fit", "strong_answer_includes": ["summary"], "common_mistakes": [], "technical_concepts": []},
            "evaluation_points": ["summary"],
        },
    )
    assert create_response.status_code == 201, create_response.text
    question_id = create_response.json()["id"]

    user_headers = await _user_headers(client, "not-admin@example.com")
    forbidden = await client.get("/api/v1/admin/interview/questions", headers=user_headers)
    assert forbidden.status_code in (401, 403)

    update_response = await client.put(
        f"/api/v1/admin/interview/questions/{question_id}", headers=admin_headers, json={"is_active": False}
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    delete_response = await client.delete(f"/api/v1/admin/interview/questions/{question_id}", headers=admin_headers)
    assert delete_response.status_code == 204


async def _register_admin_and_login(client: AsyncClient, db_session: AsyncSession, email: str = "int-admin@example.com") -> dict:
    from app.models.admin_user import AdminRole
    from app.repositories.admin_user_repository import AdminUserRepository
    from app.security.password import hash_password

    repo = AdminUserRepository(db_session)
    await repo.create(email=email, hashed_password=hash_password("adminpass1"), role=AdminRole.ADMIN)
    await db_session.commit()
    response = await client.post("/api/v1/admin/auth/login", json={"email": email, "password": "adminpass1"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
