"""Discovery pipeline, review workflow and app integration (spec §65-70). Sources are mocked."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.http_client import reset_http_state
from app.ingestion.research.providers import MockResearchProvider
from app.main import app
from app.models.admin_ops import (
    AuditLog,
    ChangeStatus,
    ContentChange,
    ContentSource,
    DiscoveredItem,
    DiscoveredItemStatus,
    DiscoveryRun,
    DiscoveryRunStatus,
    DiscoveryRunTrigger,
    ResearchCacheEntry,
    VerificationStatus,
)
from app.models.job import ContentStatus, Job, SourceState
from app.services.discovery.pipeline import DiscoveryPipeline
from app.services.discovery.verification import verify_active_opportunities
from app.services.discovery.worker import claim_run, enqueue_due_sources, enqueue_source_run, get_discovery_task_runner, process_run
from tests.discovery_support import (
    Router,
    admin_headers,
    create_admin,
    create_company,
    create_source,
    discovery_settings,
    greenhouse_job,
    job_posting_page,
    lever_posting,
    make_client,
    rss_feed,
    user_headers,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _fresh_http_state():
    reset_http_state()
    yield
    reset_http_state()


class RecordingRunner:
    def __init__(self) -> None:
        self.run_ids: list[str] = []
        self.verifications = 0

    def enqueue(self, run_id: str) -> None:
        self.run_ids.append(run_id)

    def enqueue_verification(self, trigger=None) -> None:
        self.verifications += 1


@pytest.fixture
def runner():
    recorder = RecordingRunner()
    app.dependency_overrides[get_discovery_task_runner] = lambda: recorder
    yield recorder
    app.dependency_overrides.pop(get_discovery_task_runner, None)


async def run_source(db: AsyncSession, source_id: str, router: Router, *, settings=None, research=None) -> DiscoveryRun:
    source = await db.get(ContentSource, source_id)
    run, _ = await enqueue_source_run(db, source, trigger=DiscoveryRunTrigger.MANUAL)
    pipeline = DiscoveryPipeline(db, settings=settings or discovery_settings(), http_client_factory=lambda: make_client(router), research_provider=research)
    claimed = await claim_run(db, run.id)
    return await pipeline.execute(claimed)


async def lever_setup(client: AsyncClient, db: AsyncSession, **source_fields):
    await create_admin(db)
    headers = await admin_headers(client)
    company_id = await create_company(client, headers, name="Acme Energy", website_url="https://acme-energy.com")
    source = await create_source(
        client, headers, name="Acme on Lever", organization="Acme Energy", url="https://jobs.lever.co/acme",
        source_type="LEVER", company_id=company_id, content_types=["JOB", "INTERNSHIP"], **source_fields,
    )
    return headers, company_id, source


def lever_router(postings: list[dict]) -> Router:
    return Router().json("GET", "https://api.lever.co/v0/postings/acme", postings)


async def queue_items(db: AsyncSession, source_id: str) -> list[DiscoveredItem]:
    return list((await db.execute(select(DiscoveredItem).where(DiscoveredItem.source_id == source_id).order_by(DiscoveredItem.created_at))).scalars().all())


# --------------------------------------------------------------------------------------------------
# §68 Admin → mobile acceptance flow
# --------------------------------------------------------------------------------------------------

async def test_discovered_job_flows_from_queue_to_mobile_save_and_application(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, source = await lever_setup(client, db_session)
    run = await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]))
    assert run.status == DiscoveryRunStatus.SUCCEEDED
    assert (run.items_found, run.items_new) == (1, 1)

    # Not published by default — the public feed is still empty.
    assert (await client.get("/api/v1/jobs")).json()["total"] == 0

    queue = (await client.get("/api/v1/admin/discovery", headers=headers)).json()
    assert queue["total"] == 1
    item = queue["items"][0]
    assert item["status"] == "VERIFIED" and item["verification_status"] == "SOURCE_VERIFIED"
    assert item["canonical_url"] == "https://jobs.lever.co/acme/p1/apply"

    review = (await client.get(f"/api/v1/admin/discovery/{item['id']}/review", headers=headers)).json()
    assert review["evidence"]["source_quality"] == "Official ATS (Lever)"
    assert review["evidence"]["matched_organization"]["name"] == "Acme Energy"
    assert review["evidence"]["external_id"] == "p1"
    assert review["extracted"]["title"] == "Process Technician"
    assert review["can_publish"] is True

    published = await client.post(f"/api/v1/admin/discovery/{item['id']}/publish", headers=headers, json={})
    assert published.status_code == 200, published.text
    job_id = published.json()["entity_id"]

    feed = (await client.get("/api/v1/jobs")).json()
    assert feed["total"] == 1
    card = feed["items"][0]
    assert card["availability"] == "ACTIVE" and card["is_official_source"] is True

    user = await user_headers(client)
    detail = (await client.get(f"/api/v1/jobs/{job_id}", headers=user)).json()
    assert detail["application_url"] == "https://jobs.lever.co/acme/p1/apply"  # official source opens
    assert detail["requirements"] == ["HND or B.Sc in engineering", "Knowledge of PLC systems"]
    assert detail["salary_min"] is None

    assert (await client.post(f"/api/v1/jobs/{job_id}/save", headers=user)).status_code == 204
    application = await client.post("/api/v1/applications", headers=user, json={"job_id": job_id})
    assert application.status_code == 201, application.text

    audit_actions = {a.action for a in (await db_session.execute(select(AuditLog))).scalars().all()}
    assert {"source_created", "discovery_run", "discovery_published"} <= audit_actions


async def test_rerunning_an_unchanged_source_creates_nothing_new(client: AsyncClient, db_session: AsyncSession) -> None:
    _, _, source = await lever_setup(client, db_session)
    router = lever_router([lever_posting("p1", "Process Technician"), lever_posting("p2", "Instrument Technician")])
    await run_source(db_session, source["id"], router)
    second = await run_source(db_session, source["id"], router)
    assert (second.items_found, second.items_new, second.items_duplicate) == (2, 0, 0)
    assert second.stats_json["unchanged"] == 2
    assert len(await queue_items(db_session, source["id"])) == 2


async def test_board_embedded_in_company_website_is_verified_and_queue_refreshes_location(client: AsyncClient, db_session: AsyncSession) -> None:
    """Real boards (One Acre Fund, Teach For All) link each job to the employer's own site."""
    await create_admin(db_session)
    headers = await admin_headers(client)
    company_id = await create_company(client, headers, name="Acme Energy", website_url="https://acme-energy.com")
    source = await create_source(
        client, headers, name="Acme on Greenhouse", organization="Acme Energy", url="https://boards.greenhouse.io/acme",
        source_type="GREENHOUSE", company_id=company_id,
    )
    board = "https://boards-api.greenhouse.io/v1/boards/acme/jobs"
    jobs = [
        greenhouse_job(1, "Field Officer", absolute_url="https://www.acme-energy.com/vacancies/?gh_jid=1", location={"name": "Lagos, Nigeria or Nairobi, Kenya"}),
        greenhouse_job(2, "Data Analyst", absolute_url="https://unrelated-jobs.example/acme/2"),
    ]
    await run_source(db_session, source["id"], Router().json("GET", board, {"jobs": jobs}))
    embedded, elsewhere = await queue_items(db_session, source["id"])
    assert (embedded.status, embedded.verification_status.value) == (DiscoveredItemStatus.VERIFIED, "SOURCE_VERIFIED")
    assert embedded.country is None  # two countries named: not guessed
    assert elsewhere.status == DiscoveredItemStatus.NEEDS_REVIEW and "LISTING_OFF_SOURCE_DOMAIN" in elsewhere.evidence_json["flags"]

    jobs[0]["location"] = {"name": "Kano, Nigeria"}
    second = await run_source(db_session, source["id"], Router().json("GET", board, {"jobs": jobs}))
    assert second.items_updated == 1
    await db_session.refresh(embedded)
    assert (embedded.location, embedded.country, embedded.extracted_data_json["country"]) == ("Kano, Nigeria", "Nigeria", "Nigeria")


# --------------------------------------------------------------------------------------------------
# §65 Deduplication
# --------------------------------------------------------------------------------------------------

async def test_same_requisition_from_another_source_updates_instead_of_duplicating(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, source = await lever_setup(client, db_session)
    await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]))
    item = (await queue_items(db_session, source["id"]))[0]
    publish = await client.post(f"/api/v1/admin/discovery/{item.id}/publish", headers=headers, json={})
    job = await db_session.get(Job, publish.json()["entity_id"])
    job.requisition_id = "REQ-77"
    await db_session.commit()

    greenhouse = await create_source(
        client, headers, name="Acme on Greenhouse", organization="Acme Energy", url="https://boards.greenhouse.io/acme",
        source_type="GREENHOUSE", company_id=company_id,
    )
    router = Router().json("GET", "https://boards-api.greenhouse.io/v1/boards/acme/jobs", {"jobs": [{
        "id": 555, "title": "Process Technician (Onne)", "requisition_id": "REQ-77", "location": {"name": "Lagos, Nigeria"},
        "absolute_url": "https://boards.greenhouse.io/acme/jobs/555", "content": "<p>Same role.</p>",
    }]})
    run = await run_source(db_session, greenhouse["id"], router)
    assert run.items_new == 0
    new_item = (await queue_items(db_session, greenhouse["id"]))[0]
    assert new_item.matched_entity_id == job.id
    assert "record_same_requisition_id" in new_item.evidence_json["dedup"]
    assert (await db_session.execute(select(Job))).scalars().all() == [job]


async def test_same_canonical_url_with_tracking_parameters_is_a_duplicate(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, lever = await lever_setup(client, db_session)
    await run_source(db_session, lever["id"], lever_router([lever_posting("p1", "Process Technician")]))
    rss = await create_source(
        client, headers, name="Industry jobs feed", url="https://energyjobs.example.org/feed", source_type="RSS",
        content_types=["JOB"], discovery_method="RSS",
    )
    feed = rss_feed([("Process Technician - Acme Energy", "https://jobs.lever.co/acme/p1/apply?utm_source=feed&lever-source=energyjobs", "Role at Acme")])
    run = await run_source(db_session, rss["id"], Router().add("GET", "https://energyjobs.example.org/feed", httpx.Response(200, text=feed)))
    duplicate = (await queue_items(db_session, rss["id"]))[0]
    assert run.items_duplicate == 1
    assert duplicate.status == DiscoveredItemStatus.DUPLICATE
    assert duplicate.duplicate_of_id == (await queue_items(db_session, lever["id"]))[0].id


async def test_slightly_different_title_same_company_and_location_is_not_duplicated(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, source = await lever_setup(client, db_session)
    existing = await client.post("/api/v1/admin/jobs", headers=headers, json={
        "company_id": company_id, "title": "Senior Process Technician", "location": "Lagos, Nigeria", "country": "Nigeria",
        "employment_type": "FULL_TIME", "work_mode": "ON_SITE", "status": "PUBLISHED",
    })
    run = await run_source(db_session, source["id"], lever_router([lever_posting("p9", "Process Technician (Senior)")]))
    item = (await queue_items(db_session, source["id"]))[0]
    assert run.items_new == 0
    assert item.matched_entity_id == existing.json()["id"]
    assert "record_similar_title_same_company_location" in item.evidence_json["dedup"]
    assert len((await db_session.execute(select(Job))).scalars().all()) == 1


# --------------------------------------------------------------------------------------------------
# §66 Change detection
# --------------------------------------------------------------------------------------------------

async def test_deadline_change_at_source_is_detected_reviewed_applied_and_recorded(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    company_id = await create_company(client, headers, name="Acme Energy", website_url="https://acme-energy.com")
    page_url = "https://careers.acme-energy.com/jobs/ACME-001"
    source = await create_source(
        client, headers, name="Acme careers", organization="Acme Energy", url="https://careers.acme-energy.com/jobs",
        source_type="OFFICIAL_CAREER_PAGE", company_id=company_id, discovery_method="STRUCTURED_DATA", adapter_config_json={"pages": [page_url]},
    )
    page = {"html": job_posting_page("Instrumentation Technician", valid_through="2026-09-30T23:59:00Z")}
    router = Router().add("GET", page_url, lambda request: httpx.Response(200, text=page["html"]))

    await run_source(db_session, source["id"], router)
    item = (await queue_items(db_session, source["id"]))[0]
    job_id = (await client.post(f"/api/v1/admin/discovery/{item.id}/publish", headers=headers, json={})).json()["entity_id"]

    page["html"] = job_posting_page("Instrumentation Technician", valid_through="2026-10-07T23:59:00Z")
    run = await run_source(db_session, source["id"], router)
    assert run.items_updated == 1

    changes = (await client.get("/api/v1/admin/discovery/changes", headers=headers, params={"entity_type": "JOB", "entity_id": job_id, "status": "PENDING"})).json()
    deadline_change = next(c for c in changes if c["field"] == "application_deadline")
    assert deadline_change["old_value"].startswith("2026-09-30") and deadline_change["new_value"].startswith("2026-10-07")

    # Detected, not silently applied.
    job = await db_session.get(Job, job_id)
    await db_session.refresh(job)
    assert job.application_deadline.date().isoformat() == "2026-09-30"

    applied = await client.post(f"/api/v1/admin/discovery/changes/{deadline_change['id']}/apply", headers=headers)
    assert applied.status_code == 200 and applied.json()["status"] == "APPLIED"
    detail = (await client.get(f"/api/v1/jobs/{job_id}")).json()
    assert detail["application_deadline"].startswith("2026-10-07")

    history = (await client.get("/api/v1/admin/discovery/changes", headers=headers, params={"entity_id": job_id})).json()
    assert any(c["field"] == "application_deadline" and c["status"] == "APPLIED" for c in history)
    actions = {a.action for a in (await db_session.execute(select(AuditLog))).scalars().all()}
    assert "deadline_changed" in actions


# --------------------------------------------------------------------------------------------------
# §67 Expiry / source removal
# --------------------------------------------------------------------------------------------------

async def test_listing_removed_at_source_is_kept_hidden_then_expired_on_confirmation(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session)
    both = lever_router([lever_posting("p1", "Process Technician"), lever_posting("p2", "Instrument Technician")])
    await run_source(db_session, source["id"], both)
    first = (await queue_items(db_session, source["id"]))[0]
    job_id = (await client.post(f"/api/v1/admin/discovery/{first.id}/publish", headers=headers, json={})).json()["entity_id"]
    user = await user_headers(client)
    await client.post(f"/api/v1/jobs/{job_id}/save", headers=user)

    run = await run_source(db_session, source["id"], lever_router([lever_posting("p2", "Instrument Technician")]))
    assert run.items_removed >= 1

    job = await db_session.get(Job, job_id)
    await db_session.refresh(job)
    assert job.source_state == SourceState.SOURCE_REMOVED
    assert job.status == ContentStatus.PUBLISHED  # not destroyed or expired before confirmation
    assert (await client.get("/api/v1/jobs")).json()["total"] == 0  # no Apply sent to a dead listing
    detail = await client.get(f"/api/v1/jobs/{job_id}", headers=user)
    assert detail.status_code == 200 and detail.json()["availability"] == "UNAVAILABLE"
    assert (await client.get("/api/v1/me/saved-jobs", headers=user)).json()["total"] == 1  # history kept

    confirmed = await client.post(f"/api/v1/admin/discovery/records/JOB/{job_id}/source-state", headers=headers, json={"confirm": True})
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "EXPIRED"
    assert (await client.get(f"/api/v1/jobs/{job_id}", headers=user)).status_code == 200


async def test_false_removal_can_be_dismissed_and_listing_returns(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session)
    await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician"), lever_posting("p2", "Operator")]))
    first = (await queue_items(db_session, source["id"]))[0]
    job_id = (await client.post(f"/api/v1/admin/discovery/{first.id}/publish", headers=headers, json={})).json()["entity_id"]
    await run_source(db_session, source["id"], lever_router([lever_posting("p2", "Operator")]))
    dismissed = await client.post(f"/api/v1/admin/discovery/records/JOB/{job_id}/source-state", headers=headers, json={"confirm": False})
    assert dismissed.json()["source_state"] == "ACTIVE"
    assert (await client.get("/api/v1/jobs")).json()["total"] == 1


async def test_empty_listing_from_source_does_not_mass_remove(client: AsyncClient, db_session: AsyncSession) -> None:
    _, _, source = await lever_setup(client, db_session)
    await run_source(db_session, source["id"], lever_router([lever_posting(str(i), f"Operator {i}") for i in range(3)]))
    run = await run_source(db_session, source["id"], lever_router([]))
    assert run.items_removed == 0
    assert any("removal detection skipped" in w for w in run.stats_json["warnings"])


async def test_verification_marks_dead_closed_and_passed_listings_without_deleting(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    company_id = await create_company(client, headers, name="Delta Manufacturing")
    ids = {}
    for key, url, deadline in (
        ("gone", "https://careers.delta.example.com/jobs/1", None),
        ("closed", "https://careers.delta.example.com/jobs/2", None),
        ("blocked", "https://careers.delta.example.com/jobs/3", None),
        ("ok", "https://careers.delta.example.com/jobs/4", None),
        ("passed", "https://careers.delta.example.com/jobs/5", (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()),
    ):
        response = await client.post("/api/v1/admin/jobs", headers=headers, json={
            "company_id": company_id, "title": f"Role {key}", "employment_type": "FULL_TIME", "work_mode": "ON_SITE",
            "application_url": url, "status": "PUBLISHED", "application_deadline": deadline,
        })
        ids[key] = response.json()["id"]
    router = (
        Router()
        .add("GET", "https://careers.delta.example.com/jobs/1", httpx.Response(404))
        .add("GET", "https://careers.delta.example.com/jobs/2", httpx.Response(200, text="<p>This position has been filled.</p>"))
        .add("GET", "https://careers.delta.example.com/jobs/3", httpx.Response(403))
        .add("GET", "https://careers.delta.example.com/jobs/4", httpx.Response(200, text="<p>Apply now</p>"))
    )
    run = await verify_active_opportunities(db_session, settings=discovery_settings(), http_client=make_client(router))
    assert run.stats_json["deadline_passed"] == 1

    async def state(key):
        job = await db_session.get(Job, ids[key])
        await db_session.refresh(job)
        return job.source_state, job.status

    assert await state("gone") == (SourceState.SOURCE_REMOVED, ContentStatus.PUBLISHED)
    assert await state("closed") == (SourceState.CLOSED, ContentStatus.PUBLISHED)
    assert await state("blocked") == (SourceState.ACTIVE, ContentStatus.PUBLISHED)  # access control ≠ removal
    assert await state("ok") == (SourceState.ACTIVE, ContentStatus.PUBLISHED)
    assert await state("passed") == (SourceState.DEADLINE_PASSED, ContentStatus.EXPIRED)
    assert len((await db_session.execute(select(Job))).scalars().all()) == 5


# --------------------------------------------------------------------------------------------------
# §69 Company intelligence
# --------------------------------------------------------------------------------------------------

async def test_newsroom_announcement_reaches_feed_company_page_and_interview_research(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    company_id = await create_company(client, headers, name="Acme Energy", website_url="https://acme-energy.com")
    source = await create_source(
        client, headers, name="Acme newsroom", organization="Acme Energy", url="https://acme-energy.com/news/feed",
        source_type="OFFICIAL_NEWSROOM", company_id=company_id, discovery_method="RSS", content_types=["INTELLIGENCE"],
    )
    feed = rss_feed([("Acme Energy commissions automated production line in Onne", "https://acme-energy.com/news/automation", "The fully automated line was commissioned on 7 September.")])
    await run_source(db_session, source["id"], Router().add("GET", "https://acme-energy.com/news/feed", httpx.Response(200, text=feed)))
    item = (await queue_items(db_session, source["id"]))[0]
    assert item.item_type.value == "INTELLIGENCE"

    publish = await client.post(
        f"/api/v1/admin/discovery/{item.id}/publish", headers=headers,
        json={"career_relevance": "This development may increase the relevance of automation, controls and reliability skills."},
    )
    assert publish.status_code == 200, publish.text
    slug = publish.json()["slug"]

    feed_items = (await client.get("/api/v1/intelligence")).json()["items"]
    assert [p["slug"] for p in feed_items] == [slug]
    company_items = (await client.get("/api/v1/intelligence", params={"company_id": company_id})).json()["items"]
    assert company_items[0]["slug"] == slug
    detail = (await client.get(f"/api/v1/intelligence/{slug}")).json()
    assert detail["full_content"] is None  # never the full article
    assert detail["source_url"] == "https://acme-energy.com/news/automation"
    assert "may increase" in detail["why_it_matters"]

    user = await user_headers(client)
    application = await client.post("/api/v1/applications", headers=user, json={"company_name": "Acme Energy", "role_title": "Controls Engineer"})
    prep = (await client.get("/api/v1/interview/prep/company", headers=user, params={"application_id": application.json()["id"]})).json()
    assert prep["recent_developments"][0]["headline"] == "Acme Energy commissions automated production line in Onne"


# --------------------------------------------------------------------------------------------------
# §70 Scholarship via AI research of an official page (mock provider)
# --------------------------------------------------------------------------------------------------

async def test_official_scholarship_is_researched_reviewed_published_searched_and_saved(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    page_url = "https://scholarships.example-university.ac.uk/global-masters"
    source = await create_source(
        client, headers, name="Example University scholarships", organization="Example University", url="https://scholarships.example-university.ac.uk/",
        source_type="SCHOLARSHIP_PROVIDER", discovery_method="AI_RESEARCH", content_types=["SCHOLARSHIP"],
        adapter_config_json={"pages": [page_url]},
    )
    page_html = """<html><body><h1>Global Masters Scholarship 2027</h1>
        <p>The Global Masters Scholarship is fully funded and covers tuition, a monthly stipend and return flights.</p>
        <p>Open to graduates in Engineering and Data Science. Apply by 15 January 2027.</p></body></html>"""
    research = MockResearchProvider({page_url: [{
        "content_type": "SCHOLARSHIP", "name": "Global Masters Scholarship 2027", "provider": "Example University", "country": "United Kingdom",
        "funding_type": "FULLY_FUNDED", "funding_evidence": "The Global Masters Scholarship is fully funded and covers tuition",
        "fields_of_study": ["Engineering", "Data Science"], "deadline": "2027-01-15", "official_application_url": page_url,
        "confidence": 0.9, "evidence_quotes": ["Apply by 15 January 2027"],
    }]})
    router = Router().add("GET", page_url, httpx.Response(200, text=page_html))
    settings = discovery_settings(ai_research_enabled=True, ai_research_min_trust_level=3)
    run = await run_source(db_session, source["id"], router, settings=settings, research=research)
    assert run.items_new == 1, run.stats_json

    item = (await queue_items(db_session, source["id"]))[0]
    assert item.extracted_data_json["funding_type"] == "FULLY_FUNDED"
    assert item.evidence_json["ai_provider"] == "mock"
    assert item.confidence <= 0.75  # AI output never carries more confidence than structured data

    publish = await client.post(f"/api/v1/admin/discovery/{item.id}/publish", headers=headers, json={})
    scholarship_id = publish.json()["entity_id"]
    found = (await client.get("/api/v1/scholarships", params={"search": "global masters", "funding_type": "FULLY_FUNDED", "field_of_study": "data science"})).json()
    assert [s["id"] for s in found["items"]] == [scholarship_id]
    detail = (await client.get(f"/api/v1/scholarships/{scholarship_id}")).json()
    assert detail["official_url"] == page_url
    user = await user_headers(client)
    assert (await client.post(f"/api/v1/scholarships/{scholarship_id}/save", headers=user)).status_code == 204

    # Unchanged page → the cached research result is reused, no second provider call.
    calls_before = len(research.calls)
    await run_source(db_session, source["id"], router, settings=settings, research=research)
    assert len(research.calls) == calls_before
    assert len((await db_session.execute(select(ResearchCacheEntry))).scalars().all()) == 1


async def test_ai_research_budget_limits_items_per_run(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    pages = [f"https://careers.budget.example.com/p{i}" for i in range(3)]
    source = await create_source(
        client, headers, name="Budget co", organization="Budget Co", url="https://careers.budget.example.com/",
        source_type="OFFICIAL_CAREER_PAGE", discovery_method="AI_RESEARCH", content_types=["JOB"], adapter_config_json={"pages": pages},
    )
    router = Router()
    for i, page in enumerate(pages):
        router.add("GET", page, httpx.Response(200, text=f"<h1>Operator {i}</h1>"))
    research = MockResearchProvider({page: [{"content_type": "JOB", "title": f"Operator {i}", "company": "Budget Co"}] for i, page in enumerate(pages)})
    run = await run_source(db_session, source["id"], router, settings=discovery_settings(ai_research_enabled=True, ai_research_max_items_per_run=1), research=research)
    assert len(research.calls) == 1
    assert run.stats_json["ai_research"]["skipped"] == {"ITEM_BUDGET_EXHAUSTED": 2}


# --------------------------------------------------------------------------------------------------
# Auto-publish gates, feature flags, failures, worker
# --------------------------------------------------------------------------------------------------

async def test_nothing_auto_publishes_by_default_even_from_a_trusted_verified_source(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session, auto_publish_allowed=True, trust_level=5)
    await client.put(f"/api/v1/admin/sources/{source['id']}", headers=headers, json={"verification_status": "VERIFIED"})
    await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]))
    assert (await client.get("/api/v1/jobs")).json()["total"] == 0
    item = (await queue_items(db_session, source["id"]))[0]
    assert "AUTO_PUBLISH_DISCOVERY is off" in item.evidence_json["auto_publish_blocked_by"]


async def test_auto_publish_only_when_every_gate_passes(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session, auto_publish_allowed=True, trust_level=5)
    await client.put(f"/api/v1/admin/sources/{source['id']}", headers=headers, json={"verification_status": "VERIFIED"})
    run = await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]), settings=discovery_settings(auto_publish_discovery=True))
    assert run.stats_json["auto_published"] == 1
    assert (await client.get("/api/v1/jobs")).json()["total"] == 1


async def test_disabled_discovery_skips_runs_but_manual_content_still_works(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, source = await lever_setup(client, db_session)
    run = await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]), settings=discovery_settings(web_discovery_enabled=False))
    assert run.status == DiscoveryRunStatus.SKIPPED and run.error_code == "DISABLED"
    manual = await client.post("/api/v1/admin/jobs", headers=headers, json={
        "company_id": company_id, "title": "Manual role", "employment_type": "FULL_TIME", "work_mode": "ON_SITE", "status": "PUBLISHED",
    })
    assert manual.status_code == 201
    assert (await client.get("/api/v1/jobs")).json()["total"] == 1


async def test_rate_limited_source_backs_off(client: AsyncClient, db_session: AsyncSession) -> None:
    _, _, source = await lever_setup(client, db_session)
    router = Router().add("GET", "https://api.lever.co/v0/postings/acme", httpx.Response(429, headers={"Retry-After": "7200"}))
    run = await run_source(db_session, source["id"], router)
    assert run.status == DiscoveryRunStatus.RATE_LIMITED
    row = await db_session.get(ContentSource, source["id"])
    await db_session.refresh(row)
    assert row.consecutive_failures == 1 and row.last_error_code == "RATE_LIMITED"
    assert row.next_poll_after.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=110)


async def test_server_failure_is_recorded_on_run_and_source(client: AsyncClient, db_session: AsyncSession) -> None:
    _, _, source = await lever_setup(client, db_session)
    run = await run_source(db_session, source["id"], Router().add("GET", "https://api.lever.co/v0/postings/acme", httpx.Response(500)))
    assert run.status == DiscoveryRunStatus.FAILED and run.error_code == "SERVER_ERROR"
    row = await db_session.get(ContentSource, source["id"])
    await db_session.refresh(row)
    assert row.last_error_at is not None and row.next_poll_after is not None


async def test_run_discovery_endpoint_enqueues_and_returns_immediately(client: AsyncClient, db_session: AsyncSession, runner: RecordingRunner) -> None:
    headers, _, source = await lever_setup(client, db_session)
    response = await client.post(f"/api/v1/admin/sources/{source['id']}/run", headers=headers)
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert runner.run_ids == [response.json()["id"]]
    again = await client.post(f"/api/v1/admin/sources/{source['id']}/run", headers=headers)
    assert again.json()["id"] == response.json()["id"] and len(runner.run_ids) == 1  # no pile-up

    run_id = response.json()["id"]
    assert await claim_run(db_session, run_id) is not None
    assert await claim_run(db_session, run_id) is None  # a second worker can't claim it


async def test_process_run_records_internal_errors_on_the_run(client: AsyncClient, db_session: AsyncSession) -> None:
    _, _, source = await lever_setup(client, db_session)
    run, _ = await enqueue_source_run(db_session, await db_session.get(ContentSource, source["id"]), trigger=DiscoveryRunTrigger.MANUAL)

    class Exploding(DiscoveryPipeline):
        async def execute(self, run):
            raise RuntimeError("boom")

    result = await process_run(db_session, run.id, pipeline_factory=lambda db: Exploding(db, settings=discovery_settings()))
    assert result.status == DiscoveryRunStatus.FAILED and result.error_code == "INTERNAL_ERROR"


async def test_dispatcher_only_enqueues_due_polling_sources(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, due = await lever_setup(client, db_session, polling_enabled=True)
    await create_source(client, headers, name="Not polling", url="https://jobs.lever.co/other", source_type="LEVER")
    backing_off = await create_source(client, headers, name="Backing off", url="https://jobs.lever.co/third", source_type="LEVER", polling_enabled=True)
    row = await db_session.get(ContentSource, backing_off["id"])
    row.next_poll_after = datetime.now(timezone.utc) + timedelta(hours=1)
    await db_session.commit()
    assert await enqueue_due_sources(db_session, settings=discovery_settings()) == 1
    queued = (await db_session.execute(select(DiscoveryRun))).scalars().all()
    assert [r.source_id for r in queued] == [due["id"]]


async def test_editor_cannot_change_trust_or_auto_publish(client: AsyncClient, db_session: AsyncSession) -> None:
    _, _, source = await lever_setup(client, db_session)
    from app.models.admin_user import AdminRole

    await create_admin(db_session, email="editor@example.com", role=AdminRole.EDITOR)
    editor = await admin_headers(client, email="editor@example.com")
    response = await client.put(f"/api/v1/admin/sources/{source['id']}", headers=editor, json={"auto_publish_allowed": True})
    assert response.status_code == 403
    assert (await client.put(f"/api/v1/admin/sources/{source['id']}", headers=editor, json={"crawl_interval_minutes": 360})).status_code == 200


async def test_metrics_and_source_health(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session)
    await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]))
    metrics = (await client.get("/api/v1/admin/discovery/metrics", headers=headers)).json()
    assert metrics["active_sources"] == 1 and metrics["awaiting_review"] == 1 and metrics["discovery_runs_24h"] == 1
    assert metrics["auto_publish_enabled"] is False
    health = (await client.get("/api/v1/admin/sources", headers=headers)).json()
    assert health[0]["items_discovered"] == 1 and health[0]["last_run_status"] == "SUCCEEDED" and health[0]["trust_level"] == 4
    assert health[0]["adapter_available"] is True


async def test_company_proposal_requires_admin_confirmation(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    source = await create_source(client, headers, name="Newco on Lever", organization="Newco Robotics", url="https://jobs.lever.co/newco", source_type="LEVER")
    await run_source(db_session, source["id"], Router().json("GET", "https://api.lever.co/v0/postings/newco", [lever_posting("n1", "Robotics Technician", hostedUrl="https://jobs.lever.co/newco/n1", applyUrl="https://jobs.lever.co/newco/n1/apply")]))
    item = (await queue_items(db_session, source["id"]))[0]
    assert item.company_id is None
    proposal = item.evidence_json["proposed_company"]
    assert proposal["name"] == "Newco Robotics" and proposal["website_url"] is None  # an ATS host isn't the company's website

    blocked = await client.post(f"/api/v1/admin/discovery/{item.id}/create-draft", headers=headers, json={})
    assert blocked.status_code == 422
    company = await client.post(f"/api/v1/admin/discovery/{item.id}/create-company", headers=headers, json={"name": proposal["name"], "career_url": proposal["career_url"]})
    assert company.status_code == 201
    draft = await client.post(f"/api/v1/admin/discovery/{item.id}/create-draft", headers=headers, json={})
    assert draft.status_code == 200
    assert (await db_session.get(Job, draft.json()["draft_id"])).status == ContentStatus.DRAFT


async def test_aggregator_listing_cannot_be_published_without_official_url(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    company_id = await create_company(client, headers, name="Acme Energy")
    source = await create_source(client, headers, name="Aggregator feed", url="https://www.indeed.com/rss", source_type="AGGREGATOR", discovery_method="RSS", content_types=["JOB"])
    feed = rss_feed([("Process Technician at Acme Energy", "https://www.indeed.com/viewjob?jk=abc", "Seen on Indeed")])
    await run_source(db_session, source["id"], Router().add("GET", "https://www.indeed.com/rss", httpx.Response(200, text=feed)))
    item = (await queue_items(db_session, source["id"]))[0]
    assert "DISCOVERY_ONLY_SOURCE" in item.evidence_json["flags"]
    review = (await client.get(f"/api/v1/admin/discovery/{item.id}/review", headers=headers)).json()
    assert review["can_publish"] is False
    blocked = await client.post(f"/api/v1/admin/discovery/{item.id}/publish", headers=headers, json={"company_id": company_id})
    assert blocked.status_code == 422


async def test_pending_change_status_values_are_consistent(db_session: AsyncSession) -> None:
    assert ChangeStatus.PENDING.value == "PENDING"
    assert VerificationStatus.VERIFIED.value == "VERIFIED"
    assert (await db_session.execute(select(ContentChange))).scalars().all() == []
