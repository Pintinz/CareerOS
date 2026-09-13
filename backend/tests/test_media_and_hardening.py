import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.interview.role_mix import category_counts_for_mix, default_mix_for
from app.models.question import Question, QuestionCategory, QuestionDifficulty, QuestionOption
from tests.test_interview import _create_category as _create_interview_category
from tests.test_interview import _register_admin_and_login
from tests.test_jobs import _admin_headers, _create_admin, _user_headers

pytestmark = pytest.mark.asyncio

# A genuinely valid 2x2 PNG (see tests/test_uploads.py for how this was generated).
_VALID_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd49a730000001049444154789c"
    "63fccf00024c609201000d1d010382c971ff0000000049454e44ae426082"
)


# ---------------------------------------------------------------------------
# Media pipeline: metadata + validation
# ---------------------------------------------------------------------------


async def test_image_upload_returns_real_metadata_and_creates_media_asset(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_admin(db_session)
    headers = await _admin_headers(client)

    files = {"file": ("pattern.png", io.BytesIO(_VALID_PNG), "image/png")}
    response = await client.post(
        "/api/v1/admin/uploads/image", headers=headers, files=files, data={"alt_text": "A test pattern"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["width"] == 2
    assert body["height"] == 2
    assert body["mime_type"] == "image/png"
    assert body["file_size"] > 0
    assert body["alt_text"] == "A test pattern"
    assert body["media_asset_id"]


async def test_image_upload_rejects_content_disguised_as_an_image(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A file with a valid-looking extension/content-type but garbage bytes must be rejected —
    the storage provider now actually decodes the image rather than trusting headers alone."""
    await _create_admin(db_session)
    headers = await _admin_headers(client)

    files = {"file": ("fake.png", io.BytesIO(b"not actually a png just some bytes"), "image/png")}
    response = await client.post("/api/v1/admin/uploads/image", headers=headers, files=files)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Question option images + immutable session snapshot
# ---------------------------------------------------------------------------


async def test_question_and_option_images_are_snapshotted_immutably(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = QuestionCategory(name="Abstract Test", slug="abstract-image-test")
    db_session.add(category)
    await db_session.flush()

    question = Question(
        question_text="Which continues the pattern?",
        question_type="IMAGE_BASED",
        question_image_url="http://localhost:8000/uploads/original-question.png",
        question_image_alt_text="Original alt text",
        category_id=category.id,
        difficulty=QuestionDifficulty.EASY,
        marks=1.0,
        negative_marks=0.0,
        is_active=True,
        is_demo=True,
    )
    db_session.add(question)
    await db_session.flush()
    db_session.add(
        QuestionOption(
            question_id=question.id, option_image_url="http://localhost:8000/uploads/original-option.png",
            option_image_alt_text="Original option alt", is_correct=True, display_order=0,
        )
    )
    db_session.add(
        QuestionOption(question_id=question.id, option_text="Wrong", is_correct=False, display_order=1)
    )
    await db_session.commit()

    headers = await _user_headers(client, "image-snapshot@example.com")
    session_response = await client.post(
        "/api/v1/aptitude/sessions", headers=headers,
        json={"sections": ["abstract-image-test"], "difficulty": "EASY", "question_count": 1, "timing": "UNTIMED"},
    )
    assert session_response.status_code == 201, session_response.text
    session_body = session_response.json()
    assert session_body["questions"][0]["question_image_url"] == "http://localhost:8000/uploads/original-question.png"
    assert session_body["questions"][0]["question_image_alt_text"] == "Original alt text"
    option = next(o for o in session_body["questions"][0]["options"] if o["option_image_url"])
    assert option["option_image_alt_text"] == "Original option alt"

    # Now the admin edits the master question's images (e.g. re-uploads a corrected asset).
    question.question_image_url = "http://localhost:8000/uploads/EDITED-question.png"
    question.question_image_alt_text = "Edited alt text"
    db_session.add(question)
    await db_session.commit()

    # The already-created session must still show the ORIGINAL image — never the edited one.
    detail_response = await client.get(f"/api/v1/aptitude/sessions/{session_body['id']}", headers=headers)
    assert detail_response.json()["questions"][0]["question_image_url"] == "http://localhost:8000/uploads/original-question.png"
    assert detail_response.json()["questions"][0]["question_image_alt_text"] == "Original alt text"


# ---------------------------------------------------------------------------
# Offline sync: version conflict handling
# ---------------------------------------------------------------------------


async def test_star_story_update_rejects_a_stale_expected_version(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _user_headers(client, "version-conflict@example.com")
    create = await client.post(
        "/api/v1/star-stories", headers=headers,
        json={"title": "Original", "category": "ACHIEVEMENT", "situation": "s", "task": "t", "action": "a", "result": "r"},
    )
    story = create.json()
    assert story["version"] == 1

    # Someone (or another device) updates it first, bumping the version.
    first_update = await client.put(f"/api/v1/star-stories/{story['id']}", headers=headers, json={"title": "Updated elsewhere"})
    assert first_update.json()["version"] == 2

    # A stale offline edit queued against version 1 must be rejected, not silently applied.
    stale_update = await client.put(
        f"/api/v1/star-stories/{story['id']}", headers=headers,
        json={"title": "Stale offline edit", "expected_version": 1},
    )
    assert stale_update.status_code == 409

    # An edit against the current version succeeds normally.
    fresh_update = await client.put(
        f"/api/v1/star-stories/{story['id']}", headers=headers,
        json={"title": "Fresh edit", "expected_version": 2},
    )
    assert fresh_update.status_code == 200
    assert fresh_update.json()["version"] == 3


async def test_checklist_update_rejects_a_stale_expected_version(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client, "checklist-conflict@example.com")
    initial = await client.get("/api/v1/interview/prep/progress", headers=headers)
    version = initial.json()["version"]

    stale = await client.put(
        "/api/v1/interview/prep/checklist", headers=headers,
        json={"key": "understand_business", "is_done": True, "expected_version": version + 99},
    )
    assert stale.status_code == 409

    fresh = await client.put(
        "/api/v1/interview/prep/checklist", headers=headers,
        json={"key": "understand_business", "is_done": True, "expected_version": version},
    )
    assert fresh.status_code == 200
    assert fresh.json()["version"] == version + 1


# ---------------------------------------------------------------------------
# Recording metadata
# ---------------------------------------------------------------------------


async def test_recording_metadata_crud_and_isolation(client: AsyncClient, db_session: AsyncSession) -> None:
    category = await _create_interview_category(db_session, "recording-test", "Behavioral")
    from tests.test_interview import _create_question

    await _create_question(db_session, category, text="Tell me about a time...")
    await db_session.commit()

    headers_a = await _user_headers(client, "recording-a@example.com")
    headers_b = await _user_headers(client, "recording-b@example.com")

    session_response = await client.post(
        "/api/v1/interview/sessions", headers=headers_a,
        json={"categories": ["recording-test"], "difficulty": "EASY", "question_count": 1},
    )
    session = session_response.json()
    question_id = session["questions"][0]["id"]

    create = await client.post(
        "/api/v1/interview/recordings", headers=headers_a,
        json={
            "session_id": session["id"], "session_question_id": question_id,
            "local_path": "/data/user/0/com.careeros/files/recordings/abc.m4a", "duration_seconds": 96,
        },
    )
    assert create.status_code == 201, create.text
    recording = create.json()
    assert recording["upload_status"] == "local_only"
    assert recording["duration_seconds"] == 96

    # Isolation: user B cannot see, rename, or delete user A's recording.
    list_as_b = await client.get("/api/v1/interview/recordings", headers=headers_b)
    assert list_as_b.json() == []
    rename_as_b = await client.put(f"/api/v1/interview/recordings/{recording['id']}", headers=headers_b, json={"title": "hijacked"})
    assert rename_as_b.status_code == 404

    rename = await client.put(
        f"/api/v1/interview/recordings/{recording['id']}", headers=headers_a, json={"title": "My answer take 2"}
    )
    assert rename.status_code == 200
    assert rename.json()["title"] == "My answer take 2"

    delete = await client.delete(f"/api/v1/interview/recordings/{recording['id']}", headers=headers_a)
    assert delete.status_code == 204
    listing = await client.get("/api/v1/interview/recordings", headers=headers_a)
    assert listing.json() == []


# ---------------------------------------------------------------------------
# Role-specific mock-interview mix configuration
# ---------------------------------------------------------------------------


def test_default_mix_matches_role_keywords_and_sums_to_one() -> None:
    process_mix = default_mix_for(field=None, industry="Oil & Gas", job_role="Process Technician")
    assert abs(sum(process_mix.values()) - 1.0) < 1e-9
    assert process_mix["technical"] == 0.40

    general_mix = default_mix_for(field=None, industry=None, job_role="Barista")
    assert abs(sum(general_mix.values()) - 1.0) < 1e-9


def test_category_counts_for_mix_sums_exactly_to_total() -> None:
    mix = {"technical": 0.4, "behavioral": 0.25, "safety": 0.2, "hr_general": 0.15}
    counts = category_counts_for_mix(mix, 10)
    assert sum(counts.values()) == 10
    assert counts["technical"] == 4


async def test_mock_mix_preview_endpoint_returns_role_specific_distribution(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _user_headers(client, "mix-preview@example.com")
    admin_headers = await _register_admin_and_login(client, db_session, email="mix-preview-admin@example.com")
    from tests.test_jobs import _create_company, _job_payload

    company_id = await _create_company(client, admin_headers, name="Demo Mix Co")
    job_response = await client.post(
        "/api/v1/admin/jobs", headers=admin_headers,
        json=_job_payload(company_id, title="Process Technician", industry="Oil & Gas"),
    )
    job_id = job_response.json()["id"]

    response = await client.get(
        "/api/v1/interview/sessions/mock-mix-preview", headers=headers,
        params={"question_count": 10, "job_id": job_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "role_default"
    assert sum(body["category_counts"].values()) == 10
