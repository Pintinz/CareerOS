"""Direct company career feeds: seed registry, sync health, draft fast-path, country-aware discovery,
verification labels and the company relationship (CAREER_SOURCE_INTEGRATION.md). Sources are mocked."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.http_client import reset_http_state
from app.models.admin_ops import ContentSource, DiscoveredItemStatus, SourceReadiness
from app.models.company import Company
from app.models.job import ContentStatus, Job
from app.services.discovery.review import ContentSourceService
from app.services.discovery.source_seed import SeedPack, import_career_sources, load_seed
from tests.discovery_support import Router, lever_posting, make_client
from tests.test_discovery_pipeline import lever_router, lever_setup, queue_items, run_source

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _fresh_http_state():
    reset_http_state()
    yield
    reset_http_state()


def pack(**overrides) -> SeedPack:
    entries = [
        {"company": "Acme Energy", "industry": "Energy", "career_url": "https://careers.acme-energy.com/", "url": "https://jobs.lever.co/acme",
         "source_type": "LEVER", "ats_provider": "LEVER", "readiness": "READY_STRUCTURED", "readiness_note": "Public Lever board.",
         "polling_enabled": True, "poll_interval_minutes": 360},
        {"company": "Blocked Corp", "career_url": "https://careers.blocked.example/", "readiness": "BLOCKED", "readiness_note": "HTTP 403 when checked.",
         "polling_enabled": True},
    ]
    return SeedPack.model_validate({"version": 1, "checked_at": "2026-09-15", "defaults": {"adapter_config": {"country_filter": ["AFRICA"]}}, "sources": entries, **overrides})


# ---------------------------------------------------------------------------------------------
# Seed registry
# ---------------------------------------------------------------------------------------------

async def test_bundled_starter_pack_is_valid_and_only_polls_verified_sources() -> None:
    starter = load_seed()
    assert len(starter.sources) >= 70
    urls = [entry.fetch_url for entry in starter.sources]
    assert len(urls) == len(set(urls))
    for entry in starter.sources:
        assert entry.readiness_note, entry.company  # every classification says why
        if entry.polling_enabled:
            assert entry.automated, f"{entry.company} is polled but not verified as fetchable"


async def test_seed_import_is_idempotent_and_respects_admin_choices(db_session: AsyncSession) -> None:
    first = await import_career_sources(db_session, pack(), admin_id=None)
    assert (first.companies_created, first.sources_created) == (2, 2)

    sources = {s.organization: s for s in (await db_session.execute(select(ContentSource))).scalars()}
    ready, blocked = sources["Acme Energy"], sources["Blocked Corp"]
    assert (ready.readiness, ready.ats_provider, ready.polling_enabled, ready.crawl_interval_minutes) == (SourceReadiness.READY_STRUCTURED, "LEVER", True, 360)
    assert ready.adapter_config_json == {"country_filter": ["AFRICA"]}
    assert (blocked.readiness, blocked.polling_enabled, blocked.discovery_method.value) == (SourceReadiness.BLOCKED, False, "MANUAL")
    assert ready.company_id == (await db_session.execute(select(Company.id).where(Company.name == "Acme Energy"))).scalar_one()

    # An admin pauses polling; re-importing a refreshed pack updates audit metadata only.
    ready.polling_enabled = False
    await db_session.commit()
    refreshed = pack()
    refreshed.sources[0].readiness_note = "Public Lever board (re-checked)."
    second = await import_career_sources(db_session, refreshed, admin_id=None)
    assert (second.companies_created, second.sources_created, second.sources_updated, second.sources_unchanged) == (0, 0, 1, 1)
    await db_session.refresh(ready)
    assert ready.readiness_note == "Public Lever board (re-checked)." and ready.polling_enabled is False

    dry = await import_career_sources(db_session, pack(), admin_id=None, dry_run=True)
    assert dry.dry_run is True and dry.sources_created == 0


async def test_import_seed_endpoint_requires_an_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    from tests.discovery_support import admin_headers, create_admin
    from app.models.admin_user import AdminRole

    await create_admin(db_session, email="editor@example.com", role=AdminRole.EDITOR)
    editor = await admin_headers(client, "editor@example.com")
    assert (await client.post("/api/v1/admin/sources/import-seed", headers=editor, json={"dry_run": True})).status_code == 403
    await create_admin(db_session)
    admin = await admin_headers(client)
    response = await client.post("/api/v1/admin/sources/import-seed", headers=admin, json={"dry_run": True})
    assert response.status_code == 200 and response.json()["dry_run"] is True and response.json()["sources_created"] >= 70


# ---------------------------------------------------------------------------------------------
# Sync: health, test connection, draft fast-path, country scope
# ---------------------------------------------------------------------------------------------

async def test_sync_records_http_status_items_found_and_health(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session)
    listed = (await client.get("/api/v1/admin/sources", headers=headers)).json()[0]
    assert listed["health"] == "UNKNOWN" and listed["requires_review"] is True and listed["adapter_name"] == "lever"

    await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician"), lever_posting("p2", "Operator")]))
    listed = (await client.get("/api/v1/admin/sources", headers=headers)).json()[0]
    assert (listed["health"], listed["last_http_status"], listed["items_last_found"], listed["last_run_new"]) == ("HEALTHY", 200, 2, 2)
    assert listed["company_name"] == "Acme Energy"

    failing = Router()  # every request 404s
    await run_source(db_session, source["id"], failing)
    listed = (await client.get("/api/v1/admin/sources", headers=headers)).json()[0]
    assert (listed["health"], listed["last_http_status"]) == ("DEGRADED", 404)

    await client.post(f"/api/v1/admin/sources/{source['id']}/pause", headers=headers)
    assert (await client.get("/api/v1/admin/sources", headers=headers)).json()[0]["health"] == "PAUSED"


async def test_test_connection_fetches_without_storing(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session)
    service = ContentSourceService(db_session)
    router = lever_router([lever_posting(str(i), f"Operator {i}") for i in range(8)])
    outcome = await service.test_connection(source["id"], http_client_factory=lambda: make_client(router))
    assert outcome.ok and outcome.adapter == "lever" and outcome.found == 5 and len(outcome.sample_titles) == 5
    assert await queue_items(db_session, source["id"]) == []

    broken = await service.test_connection(source["id"], http_client_factory=lambda: make_client(Router()))
    assert broken.ok is False and broken.error_code == "NOT_FOUND"


async def test_trusted_source_can_prepare_drafts_automatically(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, source = await lever_setup(client, db_session, auto_create_draft=True)
    run = await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]))
    assert run.stats_json["drafts_created"] == 1
    item = (await queue_items(db_session, source["id"]))[0]
    assert item.status == DiscoveredItemStatus.DRAFT_CREATED
    draft = await db_session.get(Job, item.created_draft_id)
    assert draft.status == ContentStatus.DRAFT and draft.company_id == company_id
    assert (await client.get("/api/v1/jobs")).json()["total"] == 0  # still needs an editor to publish

    published = await client.post(f"/api/v1/admin/discovery/{item.id}/publish", headers=headers, json={})
    assert published.status_code == 200 and (await client.get("/api/v1/jobs")).json()["total"] == 1


async def test_country_scope_keeps_out_of_scope_listings_out_of_the_queue(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session, adapter_config_json={"country_filter": ["AFRICA"]})
    postings = [
        lever_posting("ng", "Process Technician"),
        lever_posting("de", "Process Technician", country="DE", categories={"commitment": "Full-time", "location": "Hamburg, Germany"}),
    ]
    run = await run_source(db_session, source["id"], lever_router(postings))
    assert (run.items_found, run.stats_json["filtered"]) == (1, 1)
    assert [item.external_id for item in await queue_items(db_session, source["id"])] == ["ng"]


# ---------------------------------------------------------------------------------------------
# Public API: country-aware discovery, verification labels, company relationship
# ---------------------------------------------------------------------------------------------

async def test_published_import_filters_by_region_and_reflects_company_changes(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, company_id, source = await lever_setup(client, db_session)
    await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]))
    item = (await queue_items(db_session, source["id"]))[0]
    job_id = (await client.post(f"/api/v1/admin/discovery/{item.id}/publish", headers=headers, json={})).json()["entity_id"]

    assert (await client.get("/api/v1/jobs", params={"country": "Africa"})).json()["total"] == 1
    assert (await client.get("/api/v1/jobs", params={"country": "Europe"})).json()["total"] == 0
    assert (await client.get("/api/v1/jobs", params={"job_function": "operations"})).json()["total"] == 1
    assert (await client.get("/api/v1/jobs", params={"search": "operations"})).json()["total"] == 1

    card = (await client.get("/api/v1/jobs")).json()["items"][0]
    assert card["verification_status"] == "OFFICIAL_ATS" and card["company"]["logo_url"] is None
    detail = (await client.get(f"/api/v1/jobs/{job_id}")).json()
    assert detail["job_function"] == "Operations" and detail["verification_status"] == "OFFICIAL_ATS"

    # The job references the company; a new logo shows without touching the job.
    await client.put(f"/api/v1/admin/companies/{company_id}", headers=headers, json={"name": "Acme Energy", "logo_url": "https://cdn.careeros.test/acme.png"})
    assert (await client.get("/api/v1/jobs")).json()["items"][0]["company"]["logo_url"] == "https://cdn.careeros.test/acme.png"


async def test_stale_verification_is_not_presented_as_current() -> None:
    from datetime import datetime, timedelta, timezone

    from app.models.job import SourceState, SourceType
    from app.services.availability import verification_status_of

    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    job = Job(source_type=SourceType.WORKDAY, source_url="https://acme.wd3.myworkdayjobs.com/x", source_state=SourceState.ACTIVE, last_verified_at=now - timedelta(days=1))
    assert verification_status_of(job, now=now) == "OFFICIAL_ATS"
    job.last_verified_at = now - timedelta(days=30)
    assert verification_status_of(job, now=now) == "STALE"
    job.source_state = SourceState.SOURCE_REMOVED
    assert verification_status_of(job, now=now) == "SOURCE_REMOVED"
    manual = Job(source_type=SourceType.OTHER, source_url=None, is_verified=False)
    assert verification_status_of(manual, now=now) == "UNVERIFIED"


async def test_metrics_report_health_and_published_jobs_by_country_and_industry(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _, source = await lever_setup(client, db_session)
    await run_source(db_session, source["id"], lever_router([lever_posting("p1", "Process Technician")]))
    item = (await queue_items(db_session, source["id"]))[0]
    await client.post(f"/api/v1/admin/discovery/{item.id}/publish", headers=headers, json={})
    await db_session.execute(Company.__table__.update().values(industry="Energy"))
    await db_session.commit()
    metrics = (await client.get("/api/v1/admin/discovery/metrics", headers=headers)).json()
    assert metrics["healthy_sources"] == 1 and metrics["items_new_24h"] == 1 and metrics["last_run_at"]
    assert metrics["jobs_by_country"] == [{"country": "Nigeria", "count": 1}]
    assert metrics["jobs_by_industry"] == [{"industry": "Energy", "count": 1}]
    assert metrics["sources_by_readiness"] == {"UNVERIFIED": 1}
