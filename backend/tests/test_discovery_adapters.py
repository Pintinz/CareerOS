"""Source adapter + discovery HTTP client tests (spec §63). All sources are mocked fixtures."""

import json

import httpx
import pytest

from app.ingestion.adapters.ats import AshbyAdapter, GreenhouseAdapter, LeverAdapter, SmartRecruitersAdapter
from app.ingestion.adapters.base import AdapterConfigurationError, SourceSnapshot
from app.ingestion.adapters.feeds import RssAdapter, StructuredPageAdapter, feed_summary, parse_feed, stated_closing_date
from app.ingestion.adapters.workday import WorkdayAdapter
from app.ingestion.classification import classify_job_content_type, location_work_mode, normalize_work_mode, split_location
from app.ingestion.http_client import (
    InvalidResponseError,
    NetworkError,
    RateLimitedError,
    ResponseTooLargeError,
    RobotsDisallowedError,
    ServerError,
    UnsafeTargetError,
    reset_http_state,
)
from tests.discovery_support import Router, greenhouse_job, job_posting_page, lever_posting, make_client, rss_feed

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _fresh_http_state():
    reset_http_state()
    yield
    reset_http_state()


def snapshot(source_type: str, url: str, **overrides) -> SourceSnapshot:
    values = dict(
        id="src-1", name="Acme Careers", organization="Acme Energy", url=url, source_type=source_type,
        discovery_method="STRUCTURED_API", content_types=("JOB", "INTERNSHIP", "GRADUATE_PROGRAM"), adapter_config={}, trust_level=4,
    )
    values.update(overrides)
    return SourceSnapshot(**values)


# --------------------------------------------------------------------------------------------------
# Lever
# --------------------------------------------------------------------------------------------------

async def test_lever_success_maps_only_stated_facts_and_records_invalid_items() -> None:
    postings = [
        lever_posting("p1", "Process Technician", salaryRange={"min": 4_000_000, "max": 6_000_000, "currency": "NGN", "interval": "per-year-salary"}),
        lever_posting("p2", "Engineering Intern", workplaceType="unspecified", categories={"commitment": "Intern", "location": "Lagos"}),
        lever_posting("p3", "", hostedUrl="javascript:alert(1)"),  # invalid: empty title, unsafe URL
    ]
    router = Router().json("GET", "https://api.lever.co/v0/postings/acme", postings)
    async with make_client(router) as client:
        result = await LeverAdapter().discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=100)

    assert result.complete is True
    assert len(result.listings) == 2
    assert result.invalid_count == 1
    assert "p3" in result.seen_ids  # a malformed listing is never mistaken for a removed one
    job, intern = (listing.record for listing in result.listings)
    assert job.content_type == "JOB"
    assert (job.salary_min, job.salary_max, job.salary_currency, job.salary_period) == (4_000_000, 6_000_000, "NGN", "yearly")
    assert job.work_mode == "ON_SITE"
    assert job.country == "Nigeria"
    assert job.requirements == ["HND or B.Sc in engineering", "Knowledge of PLC systems"]
    assert job.application_deadline is None  # Lever doesn't state one; never invented
    assert intern.content_type == "INTERNSHIP"
    assert intern.work_mode == "UNSPECIFIED"
    assert intern.salary_min is None and intern.salary_currency is None
    # Invalid-item diagnostics carry field names only, never the untrusted values.
    assert "javascript" not in str(result.invalid)


async def test_lever_paginates_until_a_short_page() -> None:
    pages = {0: [lever_posting("a", "Operator A"), lever_posting("b", "Operator B")], 2: [lever_posting("c", "Operator C")]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages.get(int(request.url.params["skip"]), []))

    router = Router().add("GET", "https://api.lever.co/v0/postings/acme", handler)
    adapter = LeverAdapter()
    adapter.page_size = 2
    async with make_client(router) as client:
        result = await adapter.discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=100)
    assert result.pages == 2
    assert [l.record.title for l in result.listings] == ["Operator A", "Operator B", "Operator C"]
    assert result.complete is True


async def test_lever_stopping_at_max_items_disables_removal_detection() -> None:
    router = Router().json("GET", "https://api.lever.co/v0/postings/acme", [lever_posting(str(i), f"Operator {i}") for i in range(5)])
    async with make_client(router) as client:
        result = await LeverAdapter().discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=2)
    assert len(result.listings) == 2
    assert result.complete is False


async def test_adapter_requires_a_board_identifier() -> None:
    async with make_client(Router()) as client:
        with pytest.raises(AdapterConfigurationError):
            await LeverAdapter().discover(snapshot("LEVER", "https://acme-energy.com/careers"), client, max_items=10)


# --------------------------------------------------------------------------------------------------
# Greenhouse / Ashby / SmartRecruiters / Workday
# --------------------------------------------------------------------------------------------------

async def test_greenhouse_success_sanitizes_escaped_html() -> None:
    router = Router().json("GET", "https://boards-api.greenhouse.io/v1/boards/acme/jobs", {"jobs": [greenhouse_job(101, "Mechanical Technician")], "meta": {"total": 1}})
    async with make_client(router) as client:
        result = await GreenhouseAdapter().discover(snapshot("GREENHOUSE", "https://boards.greenhouse.io/acme"), client, max_items=10)
    record = result.listings[0].record
    assert record.requisition_id == "REQ-101"
    assert "alert" not in (record.description or "")
    assert "<" not in (record.description or "")
    assert "Maintain compressors" in record.description
    assert record.published_at.isoformat().startswith("2026-09-01")
    assert result.complete is True


async def test_greenhouse_no_results_is_a_complete_empty_listing() -> None:
    router = Router().json("GET", "https://boards-api.greenhouse.io/v1/boards/acme/jobs", {"jobs": [], "meta": {"total": 0}})
    async with make_client(router) as client:
        result = await GreenhouseAdapter().discover(snapshot("GREENHOUSE", "https://boards.greenhouse.io/acme"), client, max_items=10)
    assert result.listings == [] and result.complete is True


async def test_ashby_skips_unlisted_jobs_and_maps_compensation() -> None:
    payload = {"jobs": [
        {"id": "a1", "title": "Data Engineer", "isListed": True, "workplaceType": "Hybrid", "employmentType": "FullTime",
         "jobUrl": "https://jobs.ashbyhq.com/acme/a1", "applyUrl": "https://jobs.ashbyhq.com/acme/a1/application",
         "publishedAt": "2026-09-02T08:00:00Z", "descriptionPlain": "Build pipelines.",
         "address": {"postalAddress": {"addressLocality": "Berlin", "addressCountry": "DE"}},
         "compensation": {"summaryComponents": [{"compensationType": "Salary", "interval": "1 YEAR", "currencyCode": "EUR", "minValue": 70000, "maxValue": 85000}]}},
        {"id": "a2", "title": "Hidden Role", "isListed": False, "jobUrl": "https://jobs.ashbyhq.com/acme/a2"},
        {"id": "a3", "title": "Summer Intern", "isListed": True, "employmentType": "Intern", "jobUrl": "https://jobs.ashbyhq.com/acme/a3"},
    ]}
    router = Router().json("GET", "https://api.ashbyhq.com/posting-api/job-board/acme", payload)
    async with make_client(router) as client:
        result = await AshbyAdapter().discover(snapshot("ASHBY", "https://jobs.ashbyhq.com/acme"), client, max_items=10)
    assert result.filtered_count == 1
    data, intern = (l.record for l in result.listings)
    assert (data.work_mode, data.salary_min, data.salary_currency, data.country) == ("HYBRID", 70000, "EUR", "Germany")
    assert intern.content_type == "INTERNSHIP"


async def test_smartrecruiters_paginates_and_fetches_details() -> None:
    base = "https://api.smartrecruiters.com/v1/companies/acme/postings"

    def listing(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        content = [
            {"id": str(i), "name": f"Reliability Engineer {i}", "refNumber": f"R-{i}", "releasedDate": "2026-09-03T00:00:00Z",
             "location": {"city": "Aberdeen", "country": "gb"}, "typeOfEmployment": {"label": "Full-time"},
             "experienceLevel": {"id": "mid_senior_level"}}
            for i in range(3)
        ][offset: offset + 2]
        return httpx.Response(200, json={"offset": offset, "limit": 2, "totalFound": 3, "content": content})

    def detail(request: httpx.Request) -> httpx.Response:
        posting_id = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={
            "id": posting_id, "name": f"Reliability Engineer {posting_id}", "applyUrl": f"https://jobs.smartrecruiters.com/acme/{posting_id}",
            "postingUrl": f"https://jobs.smartrecruiters.com/acme/{posting_id}",
            "jobAd": {"sections": {"jobDescription": {"text": "<p>Keep rotating equipment reliable.</p>"}, "qualifications": {"text": "<ul><li>Vibration analysis</li></ul>"}}},
        })

    router = Router().add("GET", f"{base}?", listing).add("GET", f"{base}/", detail)
    adapter = SmartRecruitersAdapter()
    adapter.page_size = 2
    async with make_client(router) as client:
        result = await adapter.discover(snapshot("SMARTRECRUITERS", "https://jobs.smartrecruiters.com/acme"), client, max_items=10)
    assert result.pages == 2
    assert len(result.listings) == 3
    first = result.listings[0].record
    assert first.requirements == ["Vibration analysis"]
    assert first.experience_level is None  # "mid-senior" is ambiguous — not mapped to a guess
    assert first.country == "United Kingdom"
    assert result.complete is True


async def test_workday_adapter_reads_public_career_site_json() -> None:
    host = "https://acme.wd3.myworkdayjobs.com"
    router = (
        Router()
        .json("POST", f"{host}/wday/cxs/acme/External/jobs", {"total": 1, "jobPostings": [{"title": "Graduate Engineer Trainee Programme 2027", "externalPath": "/job/Lagos/GET_R100", "locationsText": "Lagos, Nigeria", "bulletFields": ["R100"]}]})
        .json("GET", f"{host}/wday/cxs/acme/External/job/", {"jobPostingInfo": {"id": "R100", "title": "Graduate Engineer Trainee Programme 2027", "jobDescription": "<p>Two-year rotational programme.</p>", "location": "Lagos, Nigeria", "timeType": "Full time", "jobReqId": "R100", "externalUrl": f"{host}/External/job/Lagos/GET_R100"}})
    )
    async with make_client(router) as client:
        result = await WorkdayAdapter().discover(snapshot("WORKDAY", f"{host}/en-US/External"), client, max_items=10)
    record = result.listings[0].record
    assert record.content_type == "GRADUATE_PROGRAM"
    assert record.requisition_id == "R100"
    assert record.published_at is None  # "Posted 3 days ago" style dates are never estimated
    assert result.listings[0].record.source_external_id == "/job/Lagos/GET_R100"  # stable with or without detail


# Facet shape as returned by live tenants (2026-09-15): countries nested under a location group.
WORKDAY_FACETS = [
    {"facetParameter": "jobFamilyGroup", "values": [{"descriptor": "Engineering", "id": "fam1", "count": 3}]},
    {"facetParameter": "locationMainGroup", "values": [
        {"facetParameter": "locationCountry", "descriptor": "Location Country", "values": [
            {"descriptor": "Nigeria", "id": "ng-id", "count": 2}, {"descriptor": "Germany", "id": "de-id", "count": 40},
        ]},
    ]},
]


async def test_workday_applies_the_tenants_country_facet_and_budgets_details() -> None:
    host = "https://acme.wd3.myworkdayjobs.com"
    bodies = []

    def jobs(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if not body["appliedFacets"]:
            return httpx.Response(200, json={"total": 42, "facets": WORKDAY_FACETS, "jobPostings": []})
        return httpx.Response(200, json={"total": 2, "jobPostings": [
            {"title": "Process Engineer", "externalPath": "/job/Lagos/PE_R1", "locationsText": "Lagos, Nigeria", "bulletFields": ["R1"]},
            {"title": "Field Technician", "externalPath": "/job/Bonny/FT_R2", "locationsText": "Bonny, Nigeria", "bulletFields": ["R2"]},
        ]})

    detail_calls = []

    def detail(request: httpx.Request) -> httpx.Response:
        detail_calls.append(request.url.path)
        return httpx.Response(200, json={"jobPostingInfo": {"title": "Process Engineer", "location": "Lagos, Nigeria", "jobDescription": "<p>Run the plant.</p>"}})

    router = Router().add("POST", f"{host}/wday/cxs/acme/External/jobs", jobs).add("GET", f"{host}/wday/cxs/acme/External/job/", detail)
    source = snapshot("WORKDAY", f"{host}/External", adapter_config={"country_filter": ["AFRICA"]}, known_external_ids=frozenset({"/job/Bonny/FT_R2"}))
    async with make_client(router) as client:
        result = await WorkdayAdapter().discover(source, client, max_items=10)

    assert bodies[-1]["appliedFacets"] == {"locationCountry": ["ng-id"]}  # Germany's 40 roles never fetched
    assert result.complete is True and len(result.listings) == 2
    assert detail_calls == ["/wday/cxs/acme/External/job/Lagos/PE_R1"]  # the known posting isn't re-fetched
    new, known = result.listings
    assert new.evidence["partial_record"] is False and known.evidence["partial_record"] is True
    assert known.record.country == "Nigeria"


async def test_workday_tenant_with_no_in_scope_country_is_a_complete_empty_listing() -> None:
    host = "https://acme.wd3.myworkdayjobs.com"
    router = Router().json("POST", f"{host}/wday/cxs/acme/External/jobs", {"total": 40, "facets": WORKDAY_FACETS, "jobPostings": []})
    source = snapshot("WORKDAY", f"{host}/External", adapter_config={"country_filter": ["Kenya"]})
    async with make_client(router) as client:
        result = await WorkdayAdapter().discover(source, client, max_items=10)
    assert result.listings == [] and result.complete is True


# --------------------------------------------------------------------------------------------------
# HTTP client behaviour: 429, 5xx, network failure, invalid data, robots, SSRF, size
# --------------------------------------------------------------------------------------------------

async def test_short_retry_after_is_honoured_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json=[lever_posting("p1", "Operator")])

    slept: list[float] = []

    async def record_sleep(seconds: float) -> None:
        slept.append(seconds)

    router = Router().add("GET", "https://api.lever.co/v0/postings/acme", handler)
    async with make_client(router, sleep=record_sleep) as client:
        result = await LeverAdapter().discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=10)
    assert len(result.listings) == 1
    assert 2.0 in slept


async def test_long_retry_after_stops_with_rate_limited() -> None:
    router = Router().add("GET", "https://api.lever.co/v0/postings/acme", httpx.Response(429, headers={"Retry-After": "3600"}))
    async with make_client(router) as client:
        with pytest.raises(RateLimitedError) as exc:
            await LeverAdapter().discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=10)
    assert exc.value.retry_after_seconds == 3600


async def test_server_errors_retry_with_a_bound_then_fail() -> None:
    router = Router().add("GET", "https://api.lever.co/v0/postings/acme", httpx.Response(503))
    async with make_client(router) as client:
        with pytest.raises(ServerError):
            await LeverAdapter().discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=10)
        lever_calls = [r for r in router.requests if r.url.path.startswith("/v0/postings")]
        assert len(lever_calls) == 3


async def test_network_failure_is_reported_not_raised_raw() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        raise httpx.ConnectError("connection refused")

    async with make_client(Router().add("GET", "https://api.lever.co", handler)) as client:
        with pytest.raises(NetworkError):
            await LeverAdapter().discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=10)


async def test_malformed_json_is_invalid_response() -> None:
    router = Router().add("GET", "https://api.lever.co/v0/postings/acme", httpx.Response(200, text="{not json"))
    async with make_client(router) as client:
        with pytest.raises(InvalidResponseError):
            await LeverAdapter().discover(snapshot("LEVER", "https://jobs.lever.co/acme"), client, max_items=10)


async def test_robots_disallow_is_respected() -> None:
    router = Router().add("GET", "https://careers.acme-energy.com/robots.txt", httpx.Response(200, text="User-agent: *\nDisallow: /jobs"))
    router.add("GET", "https://careers.acme-energy.com/jobs", httpx.Response(200, text="<html></html>"))
    async with make_client(router) as client:
        with pytest.raises(RobotsDisallowedError):
            await client.fetch("https://careers.acme-energy.com/jobs/1")
    assert not any(r.url.path.startswith("/jobs") for r in router.requests)


async def test_unreachable_robots_fails_closed() -> None:
    router = Router().add("GET", "https://careers.acme-energy.com/robots.txt", httpx.Response(503))
    async with make_client(router) as client:
        with pytest.raises(RobotsDisallowedError):
            await client.fetch("https://careers.acme-energy.com/jobs/1")


async def test_private_addresses_and_redirects_to_them_are_blocked() -> None:
    async def private_resolver(host: str) -> list[str]:
        return ["10.0.0.5"]

    async with make_client(Router(), resolver=private_resolver) as client:
        with pytest.raises(UnsafeTargetError):
            await client.fetch("https://intranet.acme-energy.com/")

    router = Router().add("GET", "https://careers.acme-energy.com/jobs", httpx.Response(302, headers={"Location": "http://169.254.169.254/latest/meta-data"}))
    async with make_client(router) as client:
        with pytest.raises(UnsafeTargetError):
            await client.fetch("https://careers.acme-energy.com/jobs")


async def test_oversized_response_is_rejected() -> None:
    router = Router().add("GET", "https://careers.acme-energy.com/big", httpx.Response(200, content=b"x" * 5000))
    async with make_client(router, max_response_bytes=1000) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.fetch("https://careers.acme-energy.com/big")


# --------------------------------------------------------------------------------------------------
# RSS and structured pages
# --------------------------------------------------------------------------------------------------

async def test_newsroom_rss_keeps_significant_developments_only() -> None:
    feed = rss_feed([
        ("Acme Energy commissions automated production line in Onne", "https://acme-energy.com/news/automation", "The line was commissioned this week."),
        ("Acme Energy appoints new Chief Executive Officer", "https://acme-energy.com/news/ceo", "The board appointed a new CEO."),
        ("Five reasons our customers love us", "https://acme-energy.com/news/marketing", "Brand story."),
    ])
    router = Router().add("GET", "https://acme-energy.com/news/feed", httpx.Response(200, text=feed))
    source = snapshot("OFFICIAL_NEWSROOM", "https://acme-energy.com/news/feed", discovery_method="RSS", content_types=("INTELLIGENCE",))
    async with make_client(router) as client:
        result = await RssAdapter().discover(source, client, max_items=10)
    assert result.complete is False  # feeds are rolling windows
    assert result.filtered_count == 1
    categories = {l.record.headline: l.record.category for l in result.listings}
    assert categories["Acme Energy commissions automated production line in Onne"] in ("PLANT_EXPANSION", "AUTOMATION")
    assert categories["Acme Energy appoints new Chief Executive Officer"] == "LEADERSHIP"
    assert all(l.record.career_relevance is None for l in result.listings)  # interpretation is never auto-written from RSS


async def test_feed_with_entity_expansion_is_rejected() -> None:
    bomb = '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]><rss><channel><item><title>&lol2;</title></item></channel></rss>'
    with pytest.raises(InvalidResponseError):
        parse_feed(bomb.encode())


async def test_structured_page_extracts_job_posting_and_flags_unstructured_pages() -> None:
    router = (
        Router()
        .add("GET", "https://careers.acme-energy.com/jobs/ACME-001", httpx.Response(200, text=job_posting_page("Instrumentation Technician", valid_through="2026-09-30T23:59:00Z")))
        .add("GET", "https://careers.acme-energy.com/jobs/plain", httpx.Response(200, text="<html><body><h1>Careers</h1></body></html>"))
    )
    source = snapshot(
        "OFFICIAL_CAREER_PAGE", "https://careers.acme-energy.com/jobs", discovery_method="STRUCTURED_DATA",
        adapter_config={"pages": ["https://careers.acme-energy.com/jobs/ACME-001", "https://careers.acme-energy.com/jobs/plain", "https://evil.example.org/job"]},
    )
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(source, client, max_items=10)
    record = result.listings[0].record
    assert record.title == "Instrumentation Technician"
    assert record.application_deadline.isoformat().startswith("2026-09-30")
    assert record.country == "Nigeria"
    assert [url for url, _ in result.unstructured_pages] == ["https://careers.acme-energy.com/jobs/plain"]
    assert any("outside the source's domain" in w for w in result.warnings)


# --------------------------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("title", "employment", "expected"),
    [
        ("Graduate Engineer Trainee Programme 2027", None, "GRADUATE_PROGRAM"),
        ("Shell Graduate Programme – Engineering", None, "GRADUATE_PROGRAM"),
        ("Senior Manager, Graduate Programme", None, "JOB"),  # experienced hire running a programme
        ("Summer Internship – Finance", None, "INTERNSHIP"),
        ("Internal Auditor", None, "JOB"),  # "internal" is not "intern"
        ("Process Technician", "INTERNSHIP", "INTERNSHIP"),
        ("Process Technician", None, "JOB"),
        ("Management Trainee Programme – Lagos", None, "TRAINEE_PROGRAM"),
        ("Graduate Trainee – Finance", None, "GRADUATE_PROGRAM"),
        ("Electrical Apprenticeship 2027", None, "APPRENTICESHIP"),
        ("Senior Apprenticeship Coordinator", None, "JOB"),  # runs the scheme; not an apprenticeship
        ("Software Engineering Intern", None, "INTERNSHIP"),
        ("Senior Mechanical Engineer", None, "JOB"),
    ],
)
async def test_classification_is_conservative(title, employment, expected) -> None:
    assert classify_job_content_type(title, employment_type=employment) == expected


async def test_unclear_work_mode_stays_unspecified() -> None:
    assert normalize_work_mode(None) == "UNSPECIFIED"
    assert normalize_work_mode("flexible") == "UNSPECIFIED"
    assert normalize_work_mode("On-site") == "ON_SITE"


# Location strings as real Greenhouse boards publish them (observed during live QA, 2026-09-15).
@pytest.mark.parametrize(
    "location, expected",
    [
        ("Lagos, Lagos State, Nigeria", ("Lagos", "Lagos State", "Nigeria")),
        ("Kampala, Uganda", ("Kampala", None, "Uganda")),
        ("Nigeria", (None, None, "Nigeria")),
        ("Austin, TX", ("Austin", "TX", None)),
        ("Remote, Nigeria", (None, None, "Nigeria")),
        ("Remote USA", (None, None, "United States")),
        ("Goma/Bukavu/Kinshasa, DRC", (None, None, "Democratic Republic of the Congo")),
        ("Jinja, Kampala Uganda", ("Jinja", None, "Uganda")),
        ("Kano, Nigeria or Jigawa, Nigeria or Gombe, Nigeria", (None, None, "Nigeria")),
        # Several places: no single city, and no country unless they all share one.
        ("Lagos, Nigeria or Nairobi, Kenya", (None, None, None)),
        ("Kenya, Rwanda, Malawi, Zambia, Tanzania", (None, None, None)),
        ("Remote locations: Australia, Bangladesh, Ghana, Kenya, Zambia", (None, None, None)),
        ("Home based - EMEA; Office Based - London, UK", (None, None, None)),
        ("Kigali,Rwanda Kigali, Rwanda, or flexible based on existing work authorization", (None, None, None)),
        # Placeholders and unknown text are never stored as a country.
        ("City, Country", ("City", None, None)),
        ("Program Country", (None, None, None)),
        ("Kinshasa, Democratic Republic of Congo.", ("Kinshasa", None, "Democratic Republic of the Congo")),
    ],
)
async def test_split_location_only_returns_recognized_single_countries(location, expected) -> None:
    assert split_location(location) == expected


async def test_location_work_mode_requires_explicit_prefix() -> None:
    assert location_work_mode("Remote, Nigeria") == "REMOTE"
    assert location_work_mode("Home based - EMEA") == "REMOTE"
    assert location_work_mode("Hybrid - Cape Town") == "HYBRID"
    assert location_work_mode("Cape Town") == "UNSPECIFIED"
    assert location_work_mode(None) == "UNSPECIFIED"


async def test_feed_summary_drops_cms_boilerplate() -> None:
    # As published by WordPress newsroom feeds (observed during live QA, 2026-09-15).
    raw = "<p>Investment supports a women-led agribusiness.</p><p>The post Acme invests in Pullus appeared first on Acme.</p>"
    assert feed_summary(raw) == "Investment supports a women-led agribusiness."
    assert feed_summary("Canonical announces certified images for the new board [&#8230;]") == "Canonical announces certified images for the new board"
    assert feed_summary(None) is None



# Shaped like a Flair-hosted careers board (observed during live QA, 2026-09-15): a listing page linking
# to one page per opening, each with JobPosting data whose HTML fields are entity-escaped and whose
# closing date is only stated in the posting text.
def flair_position(identifier: str, title: str) -> str:
    import html as _html
    import json as _json

    data = {
        "@context": "https://schema.org", "@type": "JobPosting", "identifier": identifier, "title": title,
        "datePosted": "2026-09-01", "employmentType": "FULL_TIME",
        "description": _html.escape("<p>Join the operations team.</p><p>Maintain rotating equipment.</p>"),
        "experienceRequirements": _html.escape("<p>• OND or equivalent in Mechanical Engineering</p><p>• 3 years in oil and gas operations</p>"),
        "jobBenefits": _html.escape("<p>Equal Opportunity Employer.</p><p><strong>Application Closing Date: </strong><strong>25th September 2026</strong></p>"),
        "hiringOrganization": {"@type": "Organization", "name": "Acme Energy"},
        "jobLocation": {"@type": "Place", "name": "Port Harcourt", "address": {"@type": "PostalAddress"}},
    }
    return f'<html><head><script type="application/ld+json">{_json.dumps(data)}</script></head><body><h1>{title}</h1></body></html>'


LISTING = """<html><body>
  <a href="/positions/A1">Operations Technician</a> <a href="/positions/A2#apply">Pipeline Engineer</a>
  <a href="/positions/A1">Operations Technician (duplicate link)</a> <a href="/about">About</a>
  <a href="https://other-employer.careers.flair.hr/positions/X9">Another employer's job</a>
</body></html>"""


def flair_source():
    return snapshot(
        "OFFICIAL_CAREER_PAGE", "https://acme.careers.flair.hr/", discovery_method="STRUCTURED_DATA",
        adapter_config={"listing_pages": ["https://acme.careers.flair.hr/"], "job_link_contains": "/positions/", "listing_complete": True},
    )


async def test_structured_page_follows_openings_from_a_listing_page() -> None:
    router = (
        Router()
        .add("GET", "https://acme.careers.flair.hr/", httpx.Response(200, text=LISTING))
        .add("GET", "https://acme.careers.flair.hr/positions/A1", httpx.Response(200, text=flair_position("A1", "Operations Technician")))
        .add("GET", "https://acme.careers.flair.hr/positions/A2", httpx.Response(200, text=flair_position("A2", "Pipeline Engineer")))
    )
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(flair_source(), client, max_items=10)
    assert [listing.record.title for listing in result.listings] == ["Operations Technician", "Pipeline Engineer"]
    assert result.complete is True and result.seen_ids == {"A1", "A2"}
    record = result.listings[0].record
    assert record.application_deadline.isoformat() == "2026-09-25T23:59:00+00:00"  # stated in the posting text
    assert (record.location, record.city, record.country) == ("Port Harcourt", None, None)  # no country invented
    assert record.experience_requirements == ["OND or equivalent in Mechanical Engineering", "3 years in oil and gas operations"]
    assert not any("other-employer" in str(request.url) for request in router.requests)


async def test_opening_that_disappears_mid_run_does_not_fail_or_count_as_complete() -> None:
    router = (
        Router()
        .add("GET", "https://acme.careers.flair.hr/", httpx.Response(200, text=LISTING))
        .add("GET", "https://acme.careers.flair.hr/positions/A1", httpx.Response(200, text=flair_position("A1", "Operations Technician")))
        .add("GET", "https://acme.careers.flair.hr/positions/A2", httpx.Response(404))
    )
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(flair_source(), client, max_items=10)
    assert len(result.listings) == 1 and result.complete is False
    assert any("could not be fetched" in w for w in result.warnings)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Application Closing Date: 25th September 2026", "2026-09-25"),
        ("Deadline: September 3, 2026.", "2026-09-03"),
        ("Applications close on 2026-10-01", "2026-10-01"),
        ("We review applications on a rolling basis.", None),
        ("Closing date: soon", None),
    ],
)
async def test_stated_closing_date(text, expected) -> None:
    found = stated_closing_date(text)
    assert (found.date().isoformat() if found else None) == expected


async def test_listing_pages_require_a_link_marker() -> None:
    from pydantic import ValidationError

    from app.schemas.admin_ops import ContentSourceCreate

    with pytest.raises(ValidationError):
        ContentSourceCreate(name="Acme", url="https://acme.careers.flair.hr/", source_type="OFFICIAL_CAREER_PAGE",
                            adapter_config_json={"listing_pages": ["https://acme.careers.flair.hr/"]})



async def test_company_careers_page_can_list_openings_hosted_on_its_board() -> None:
    company_page = '<a href="https://acme.careers.flair.hr/positions/A2">Pipeline Engineer</a> <a href="https://evil.example/positions/Z">x</a>'
    router = (
        Router()
        .add("GET", "https://acme-energy.com/careers", httpx.Response(200, text=company_page))
        .add("GET", "https://acme.careers.flair.hr/", httpx.Response(200, text='<a href="/positions/A1">Operations Technician</a>'))
        .add("GET", "https://acme.careers.flair.hr/positions/A1", httpx.Response(200, text=flair_position("A1", "Operations Technician")))
        .add("GET", "https://acme.careers.flair.hr/positions/A2", httpx.Response(200, text=flair_position("A2", "Pipeline Engineer")))
    )
    source = snapshot(
        "OFFICIAL_CAREER_PAGE", "https://acme.careers.flair.hr/", discovery_method="STRUCTURED_DATA",
        adapter_config={"listing_pages": ["https://acme.careers.flair.hr/", "https://acme-energy.com/careers"], "job_link_contains": "/positions/", "listing_complete": True},
    )
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(source, client, max_items=10)
    assert result.seen_ids == {"A1", "A2"} and result.complete is True
    assert not any("evil.example" in str(request.url) for request in router.requests)


# --------------------------------------------------------------------------------------------------
# Oracle Recruiting Cloud (response shapes as returned by live Candidate Experience sites, 2026-09-15)
# --------------------------------------------------------------------------------------------------

ORC_HOST = "https://acme.fa.em2.oraclecloud.com"


def orc_router(detail_calls: list[str]) -> Router:
    def search(request: httpx.Request) -> httpx.Response:
        finder = request.url.params.get("finder", "")
        if "selectedLocationsFacet=3001" in finder:
            requisitions = [
                {"Id": "7001", "Title": "Graduate Trainee Programme 2027", "PostedDate": "2026-09-10", "PrimaryLocation": "Ikoyi, Lagos, Nigeria",
                 "PrimaryLocationCountry": "NG", "WorkplaceType": "On-site", "ShortDescriptionStr": "Two-year programme."},
                {"Id": "7002", "Title": "Network Engineer", "PostedDate": "2026-09-09", "PrimaryLocation": "Abuja, Nigeria", "PrimaryLocationCountry": "NG"},
            ]
            return httpx.Response(200, json={"items": [{"TotalJobsCount": 2, "requisitionList": requisitions}]})
        return httpx.Response(200, json={"items": [{"TotalJobsCount": 30, "requisitionList": [], "locationsFacet": [
            {"Id": 3001, "Name": "Nigeria", "TotalCount": 2}, {"Id": 3002, "Name": "Cameroon", "TotalCount": 9},
            {"Id": 3003, "Name": "Lagos, Nigeria", "TotalCount": 2},
        ]}]})

    def detail(request: httpx.Request) -> httpx.Response:
        detail_calls.append(request.url.params.get("finder", ""))
        return httpx.Response(200, json={"items": [{
            "Id": "7001", "Title": "Graduate Trainee Programme 2027", "PrimaryLocation": "Ikoyi, Lagos, Nigeria", "PrimaryLocationCountry": "NG",
            "ExternalDescriptionStr": "<p>Rotations across network, IT and commercial teams.</p>",
            "ExternalQualificationsStr": "<ul><li>First degree in engineering</li><li>NYSC completed</li></ul>",
            "InternalQualificationsStr": "<p>INTERNAL ONLY: shortlist from referrals</p>",
            "ExternalPostedStartDate": "2026-09-10T09:00:00+00:00", "ExternalPostedEndDate": "2026-09-27T20:00:00+00:00",
            "JobSchedule": "Full time", "StudyLevel": "Bachelor's Degree",
        }]})

    return (
        Router()
        .add("GET", f"{ORC_HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitions", search)
        .add("GET", f"{ORC_HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails", detail)
    )


async def test_oracle_recruiting_scopes_by_country_facet_and_reads_external_fields_only() -> None:
    from app.ingestion.adapters.oracle import OracleRecruitingAdapter

    detail_calls: list[str] = []
    source = snapshot(
        "ORACLE", f"{ORC_HOST}/hcmUI/CandidateExperience/en/sites/CX_1", adapter_config={"country_filter": ["Nigeria"]},
        known_external_ids=frozenset({"7002"}),
    )
    async with make_client(orc_router(detail_calls)) as client:
        result = await OracleRecruitingAdapter().discover(source, client, max_items=10)

    assert result.complete is True and result.seen_ids == {"7001", "7002"}
    assert len(detail_calls) == 1 and "7001" in detail_calls[0]  # only the posting CareerOS hasn't seen
    programme, engineer = (listing.record for listing in result.listings)
    assert programme.content_type == "GRADUATE_PROGRAM"
    assert programme.application_deadline.isoformat() == "2026-09-27T20:00:00+00:00"  # the posting's stated end date
    assert programme.requirements == ["First degree in engineering", "NYSC completed"]
    assert "INTERNAL" not in str(result.listings[0].raw) and "INTERNAL" not in (programme.description or "")
    assert programme.application_url == f"{ORC_HOST}/hcmUI/CandidateExperience/en/sites/CX_1/job/7001"
    assert (programme.country, engineer.country) == ("Nigeria", "Nigeria")
    assert result.listings[1].evidence["partial_record"] is True


async def test_oracle_recruiting_requires_a_candidate_experience_site() -> None:
    from app.ingestion.adapters.oracle import OracleRecruitingAdapter

    async with make_client(Router()) as client:
        with pytest.raises(AdapterConfigurationError):
            await OracleRecruitingAdapter().discover(snapshot("ORACLE", "https://careers.example.com/jobs"), client, max_items=5)


# SAP SuccessFactors career sites mark postings up with microdata (shape observed live, 2026-09-15).
CSB_JOB = """<html><body><div itemscope itemtype="http://schema.org/JobPosting">
  <span itemprop="jobLocation" itemscope itemtype="http://schema.org/Place">
    <span itemprop="address" itemscope itemtype="http://schema.org/PostalAddress"><meta itemprop="streetAddress" content="Lagos, NG"></span>
  </span>
  <meta itemprop="datePosted" content="Thu Aug 20 02:00:00 UTC 2026">
  <meta itemprop="validThrough" content="Sat Oct 31 23:00:00 UTC 2026">
  <meta itemprop="hiringOrganization" content="Acme">
  <span itemprop="title">Manager, Regulatory Compliance</span>
  <span itemprop="description"><p>Lead compliance reviews.</p><ul><li>Degree in law</li></ul></span>
</div></body></html>"""


async def test_structured_page_reads_microdata_postings() -> None:
    router = (
        Router()
        .add("GET", "https://careers.acme.com/acme/search/", httpx.Response(200, text='<a href="/acme/job/Lagos-Manager/1377383933/">Manager</a>'))
        .add("GET", "https://careers.acme.com/acme/job/", httpx.Response(200, text=CSB_JOB))
    )
    source = snapshot(
        "OFFICIAL_CAREER_PAGE", "https://careers.acme.com/acme/", discovery_method="STRUCTURED_DATA",
        adapter_config={"listing_pages": ["https://careers.acme.com/acme/search/?q=&locationsearch=Nigeria"], "job_link_contains": "/job/"},
    )
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(source, client, max_items=10)
    record = result.listings[0].record
    assert record.title == "Manager, Regulatory Compliance"
    assert (record.location, record.city, record.country) == ("Lagos, Nigeria", "Lagos", "Nigeria")
    assert record.published_at.isoformat() == "2026-08-20T02:00:00+00:00"
    assert record.application_deadline.isoformat() == "2026-10-31T23:00:00+00:00"
    assert "Degree in law" in record.description


async def test_structured_page_follows_newest_openings_from_a_sitemap_with_link_filters() -> None:
    sitemap = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://careers.acme.com/job/lagos/process-engineer/1/111</loc><lastmod>2026-09-10</lastmod></url>
      <url><loc>https://careers.acme.com/job/houston/process-engineer/1/222</loc><lastmod>2026-09-12</lastmod></url>
      <url><loc>https://careers.acme.com/job/lagos/field-operator/1/333</loc><lastmod>2026-09-14</lastmod></url>
      <url><loc>https://careers.acme.com/about</loc></url>
      <url><loc>https://evil.example/job/lagos/x/1/999</loc></url>
    </urlset>"""
    router = (
        Router()
        .add("GET", "https://careers.acme.com/sitemap.xml", httpx.Response(200, text=sitemap, headers={"content-type": "application/xml"}))
        .add("GET", "https://careers.acme.com/job/lagos/process-engineer/1/111", httpx.Response(200, text=job_posting_page("Process Engineer", valid_through="2026-10-01", identifier="111")))
        .add("GET", "https://careers.acme.com/job/lagos/field-operator/1/333", httpx.Response(200, text=job_posting_page("Field Operator", valid_through="2026-10-01", identifier="333")))
    )
    source = snapshot(
        "OFFICIAL_CAREER_PAGE", "https://careers.acme.com/", discovery_method="STRUCTURED_DATA",
        adapter_config={"sitemap_urls": ["https://careers.acme.com/sitemap.xml"], "job_link_contains": "/job/", "link_filters": ["/lagos/"]},
    )
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(source, client, max_items=10)
    assert [listing.record.title for listing in result.listings] == ["Field Operator", "Process Engineer"]  # newest first
    assert result.complete is True
    assert not any("houston" in str(r.url) or "evil.example" in str(r.url) for r in router.requests)


async def test_search_result_listing_pages_never_count_as_complete() -> None:
    router = (
        Router()
        .add("GET", "https://acme.careers.flair.hr/", httpx.Response(200, text=LISTING))
        .add("GET", "https://acme.careers.flair.hr/positions/A1", httpx.Response(200, text=flair_position("A1", "Operations Technician")))
        .add("GET", "https://acme.careers.flair.hr/positions/A2", httpx.Response(200, text=flair_position("A2", "Pipeline Engineer")))
    )
    source = snapshot(
        "OFFICIAL_CAREER_PAGE", "https://acme.careers.flair.hr/", discovery_method="STRUCTURED_DATA",
        adapter_config={"listing_pages": ["https://acme.careers.flair.hr/"], "job_link_contains": "/positions/"},
    )
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(source, client, max_items=10)
    assert len(result.listings) == 2 and result.complete is False  # a first results page may not show every opening


async def test_greenhouse_board_too_large_for_descriptions_falls_back_to_the_list() -> None:
    board = "https://boards-api.greenhouse.io/v1/boards/acme/jobs"

    def listing(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("content") == "true":
            return httpx.Response(200, content=b"x" * 2048, headers={"content-length": "999999999"})
        return httpx.Response(200, json={"jobs": [
            {"id": 1, "title": "Field Engineer", "location": {"name": "Lagos, Nigeria"}, "absolute_url": "https://boards.greenhouse.io/acme/jobs/1"},
            {"id": 2, "title": "Account Executive", "location": {"name": "Berlin, Germany"}, "absolute_url": "https://boards.greenhouse.io/acme/jobs/2"},
            {"id": 3, "title": "Operator", "location": {"name": "Abuja, Nigeria"}, "absolute_url": "https://boards.greenhouse.io/acme/jobs/3"},
        ]})

    details = []

    def detail(request: httpx.Request) -> httpx.Response:
        details.append(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(200, json={"content": "&lt;p&gt;Keep the site running.&lt;/p&gt;"})

    router = Router().add("GET", board, listing).add("GET", f"{board}/", detail)
    source = snapshot("GREENHOUSE", "https://boards.greenhouse.io/acme", adapter_config={"country_filter": ["Nigeria"]}, known_external_ids=frozenset({"3"}))
    async with make_client(router) as client:
        result = await GreenhouseAdapter().discover(source, client, max_items=10)

    assert result.complete is True and len(result.listings) == 2 and result.filtered_count == 1
    assert result.seen_ids >= {"1", "2", "3"}  # the out-of-scope Berlin role is still known to be listed
    assert details == ["1"]  # only the new, in-scope posting; Berlin and the known Abuja role aren't fetched
    engineer, operator = result.listings
    assert "Keep the site running" in (engineer.record.description or "") and engineer.evidence["partial_record"] is False
    assert operator.evidence["partial_record"] is True


async def test_microdata_address_with_postcode_keeps_the_country() -> None:
    page = CSB_JOB.replace('content="Lagos, NG"', 'content="Lagos, NG, 101001"')
    router = Router().add("GET", "https://careers.acme.com/acme/job/1/", httpx.Response(200, text=page))
    source = snapshot("OFFICIAL_CAREER_PAGE", "https://careers.acme.com/acme/", discovery_method="STRUCTURED_DATA", adapter_config={"pages": ["https://careers.acme.com/acme/job/1/"]})
    async with make_client(router) as client:
        result = await StructuredPageAdapter().discover(source, client, max_items=10)
    assert result.listings[0].record.country == "Nigeria"
