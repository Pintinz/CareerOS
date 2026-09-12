import io

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_STRONG_CV_TEXT = """
Jane Doe
jane.doe@example.com | +234 800 000 0000 | linkedin.com/in/janedoe

SUMMARY
Process Technician with 6 years of experience operating and maintaining PLC-controlled
refinery equipment, focused on preventive maintenance and HSE compliance.

EXPERIENCE
Process Technician - ExxonMobil (2019-2026)
- Operated and maintained PLC and DCS systems across the Lagos refinery, improving uptime.
- Led preventive maintenance programs that reduced unplanned downtime by 30%.
- Enforced HSE and LOTO procedures across a 40-person shift team.

EDUCATION
Bachelor of Engineering, Mechanical Engineering, University of Lagos

SKILLS
PLC, DCS, SCADA, HSE, Preventive Maintenance, P&ID, LOTO
"""

_WEAK_CV_TEXT = "Jane Doe. Looking for a job. I like people and teamwork."

_JOB_DESCRIPTION = """
We are hiring a Process Technician with at least 5 years of experience operating PLC and DCS
systems in a refinery environment. Responsibilities include preventive maintenance, HSE
compliance, and LOTO procedure enforcement. A bachelor's degree in mechanical engineering or
related field is required.
"""


async def _upload_txt_cv(client: AsyncClient, headers: dict, text: str, filename: str = "cv.txt") -> dict:
    files = {"file": (filename, io.BytesIO(text.encode("utf-8")), "text/plain")}
    response = await client.post("/api/v1/ats/cv", headers=headers, files=files)
    assert response.status_code == 201
    return response.json()


async def _user_headers(client: AsyncClient, email: str = "candidate@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "candidatepass1"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_upload_txt_cv_and_list(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    cv = await _upload_txt_cv(client, headers, _STRONG_CV_TEXT)
    assert cv["name"] == "cv.txt"

    list_response = await client.get("/api/v1/ats/cv", headers=headers)
    assert list_response.json()["total"] == 1


async def test_analyze_requires_cv_and_job_input(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    response = await client.post("/api/v1/ats/analyze", headers=headers, json={})
    assert response.status_code == 422


async def test_analyze_rejects_both_cv_sources_at_once(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    cv = await _upload_txt_cv(client, headers, _STRONG_CV_TEXT)
    response = await client.post(
        "/api/v1/ats/analyze",
        headers=headers,
        json={"cv_document_id": cv["id"], "cv_text": "also this", "job_description": _JOB_DESCRIPTION},
    )
    assert response.status_code == 422


async def test_strong_cv_scores_higher_than_weak_cv_against_same_job(client: AsyncClient) -> None:
    headers = await _user_headers(client)

    strong_response = await client.post(
        "/api/v1/ats/analyze",
        headers=headers,
        json={"cv_text": _STRONG_CV_TEXT, "job_description": _JOB_DESCRIPTION, "job_title": "Process Technician"},
    )
    weak_response = await client.post(
        "/api/v1/ats/analyze",
        headers=headers,
        json={"cv_text": _WEAK_CV_TEXT, "job_description": _JOB_DESCRIPTION, "job_title": "Process Technician"},
    )
    assert strong_response.status_code == 200
    assert weak_response.status_code == 200

    strong_score = strong_response.json()["overall_score"]
    weak_score = weak_response.json()["overall_score"]
    assert strong_score > weak_score
    assert 0 <= weak_score <= 100
    assert 0 <= strong_score <= 100

    breakdown = strong_response.json()["score_breakdown"]
    assert set(breakdown.keys()) == {
        "keyword_match", "technical_skills", "experience", "job_title",
        "formatting", "education", "completeness", "placement",
    }
    total_weight = sum(component["weight"] for component in breakdown.values())
    assert abs(total_weight - 1.0) < 1e-6


async def test_synonym_normalization_counts_as_a_match(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    cv_text = "Experienced with Programmable Logic Controller systems and planned maintenance."
    job_description = "Looking for someone skilled in PLC and preventive maintenance."

    response = await client.post(
        "/api/v1/ats/analyze",
        headers=headers,
        json={"cv_text": cv_text, "job_description": job_description},
    )
    assert response.status_code == 200
    body = response.json()
    # "plc" and "preventive maintenance" should show as strong matches via synonym canonicalization,
    # not as missing keywords, even though the literal words differ between CV and JD.
    assert "plc" in body["strong_matches"] or "preventive maintenance" in body["strong_matches"]


async def test_weak_metrics_note_present_when_no_quantified_achievements(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    response = await client.post(
        "/api/v1/ats/analyze",
        headers=headers,
        json={"cv_text": _WEAK_CV_TEXT, "job_description": _JOB_DESCRIPTION},
    )
    assert response.json()["missing_metrics_note"] is not None


async def test_analyze_against_real_job_id(client: AsyncClient, db_session) -> None:
    from tests.test_jobs import _admin_headers, _create_admin, _create_company, _job_payload

    await _create_admin(db_session)
    admin_headers = await _admin_headers(client)
    company_id = await _create_company(client, admin_headers)

    create_response = await client.post(
        "/api/v1/admin/jobs",
        headers=admin_headers,
        json=_job_payload(
            company_id,
            description="Process Technician role requiring PLC and HSE experience.",
            requirements=["PLC experience", "HSE compliance"],
        ),
    )
    job_id = create_response.json()["id"]

    headers = await _user_headers(client)
    response = await client.post(
        "/api/v1/ats/analyze", headers=headers, json={"cv_text": _STRONG_CV_TEXT, "job_id": job_id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["job_title"] == "Process Technician"


async def test_analysis_history_lists_previous_runs(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    await client.post(
        "/api/v1/ats/analyze",
        headers=headers,
        json={"cv_text": _STRONG_CV_TEXT, "job_description": _JOB_DESCRIPTION},
    )
    await client.post(
        "/api/v1/ats/analyze",
        headers=headers,
        json={"cv_text": _WEAK_CV_TEXT, "job_description": _JOB_DESCRIPTION},
    )

    history = await client.get("/api/v1/ats/analyses", headers=headers)
    assert history.json()["total"] == 2


async def test_cv_upload_rejects_oversized_or_bad_type(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    files = {"file": ("resume.exe", io.BytesIO(b"not a real cv"), "application/octet-stream")}
    response = await client.post("/api/v1/ats/cv", headers=headers, files=files)
    assert response.status_code == 422


async def test_delete_cv(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    cv = await _upload_txt_cv(client, headers, _STRONG_CV_TEXT)
    delete_response = await client.delete(f"/api/v1/ats/cv/{cv['id']}", headers=headers)
    assert delete_response.status_code == 204

    list_response = await client.get("/api/v1/ats/cv", headers=headers)
    assert list_response.json()["total"] == 0
