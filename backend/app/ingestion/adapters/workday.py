"""Workday public career sites.

Workday-hosted career sites (`{tenant}.wd{N}.myworkdayjobs.com/{site}`) are rendered from a JSON
endpoint the public page itself calls (`/wday/cxs/{tenant}/{site}/jobs`). It is public — no login,
no token — and tenant-specific, so every source is configured per employer and always subject to
robots.txt like every other fetch. Live-verified against a dozen employer tenants (2026-09-15,
CAREER_SOURCE_INTEGRATION.md); still off unless WORKDAY_DISCOVERY_ENABLED is set.

- Country scope: when a source sets `country_filter`, the tenant's own location-country facet is
  applied server-side, so a 2,000-job global board returns only the in-scope openings. Tenants
  without such a facet are paged (bounded) and filtered afterwards by the pipeline.
- Details: the listing gives title, location and path; the detail endpoint adds the description,
  requisition id, time type and dates. Detail requests are budgeted and spent on postings CareerOS
  hasn't seen yet; a known posting without a fresh detail fetch is marked partial so its stored
  facts are never replaced with the thinner listing record.
- Postings show "Posted 3 Days Ago" style dates, so `published_at` only comes from the detail
  endpoint's ISO `startDate`, never estimated from the relative label.
"""

from __future__ import annotations

import re
from urllib.parse import quote, urlsplit

from pydantic import ValidationError

from app.core.config import Settings
from app.ingestion.adapters.base import (
    AdapterConfigurationError,
    AdapterResult,
    DiscoveredListing,
    SourceAdapter,
    SourceSnapshot,
    build_record,
    path_segments,
    trim_raw,
)
from app.ingestion.classification import (
    classify_job_content_type,
    experience_level_from_title,
    normalize_employment_type,
    normalize_work_mode,
    split_location,
)
from app.ingestion.countries import match_country, region_countries
from app.ingestion.http_client import DiscoveryHttpClient, FetchError
from app.ingestion.text import clean_text, html_to_text, parse_datetime

_HOST = re.compile(r"^(?P<tenant>[a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com$", re.IGNORECASE)
_LOCALE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


def wanted_countries(filters) -> set[str]:
    wanted: set[str] = set()
    for value in filters or []:
        members = region_countries(str(value))
        if members:
            wanted |= members
        elif match_country(str(value)):
            wanted.add(match_country(str(value)))
    return wanted


def country_facets(facets) -> dict[str, list[tuple[str, str]]]:
    """{facetParameter: [(country, facet id)]} for every country-type facet, flat or nested under a
    location group (Workday tenants use both shapes)."""
    found: dict[str, list[tuple[str, str]]] = {}
    for facet in facets if isinstance(facets, list) else []:
        if not isinstance(facet, dict):
            continue
        groups = [facet] + [v for v in facet.get("values") or [] if isinstance(v, dict) and v.get("facetParameter") and v.get("values")]
        for group in groups:
            parameter = str(group.get("facetParameter") or "")
            if "country" not in parameter.lower():
                continue
            for value in group.get("values") or []:
                country = match_country(str(value.get("descriptor") or "")) if isinstance(value, dict) else None
                if country and value.get("id"):
                    found.setdefault(parameter, []).append((country, str(value["id"])))
    return found


class WorkdayAdapter(SourceAdapter):
    name = "workday"
    method = "STRUCTURED_API"
    page_size = 20
    max_pages = 10
    max_detail_fetches = 40

    def is_enabled(self, settings: Settings) -> bool:
        return settings.structured_ats_sync_enabled and settings.workday_discovery_enabled

    @staticmethod
    def _site(source: SourceSnapshot) -> tuple[str, str, str]:
        parts = urlsplit(source.url)
        host = (parts.hostname or "").lower()
        tenant = source.config("tenant")
        site = source.config("site")
        match = _HOST.match(host)
        if match and not tenant:
            tenant = match.group("tenant")
        if not site:
            segments = [s for s in path_segments(source.url) if not _LOCALE.match(s)]
            site = segments[0] if segments else None
        if not (match and tenant and site):
            raise AdapterConfigurationError("use a https://{tenant}.wdN.myworkdayjobs.com/{site} URL or set tenant/site")
        return host, tenant, site

    def validate_source(self, source: SourceSnapshot) -> None:
        self._site(source)

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        host, tenant, site = self._site(source)
        base = f"https://{host}/wday/cxs/{quote(tenant)}/{quote(site)}"
        max_pages = source.config("max_pages") or self.max_pages
        detail_budget = source.config("max_detail_fetches") or self.max_detail_fetches
        wanted = wanted_countries(source.config("country_filter"))
        result = AdapterResult()

        applied: dict[str, list[str]] = {}
        body = {"appliedFacets": applied, "limit": self.page_size, "offset": 0, "searchText": source.config("search_text") or ""}
        page = await client.post_json(f"{base}/jobs", body)
        result.pages += 1
        if wanted and isinstance(page, dict):
            facets = country_facets(page.get("facets"))
            if facets:
                parameter, values = next(iter(facets.items()))
                ids = [facet_id for country, facet_id in values if country in wanted]
                if not ids:
                    # The tenant filters by country and has no openings in scope: a complete, empty listing.
                    result.complete = True
                    return result
                applied[parameter] = ids
                page = await client.post_json(f"{base}/jobs", body)
                result.pages += 1
            else:
                result.warnings.append("tenant has no country facet; listings are filtered after fetching")

        offset, details, list_pages = 0, 0, 1
        known = source.known_external_ids
        while True:
            postings = page.get("jobPostings") if isinstance(page, dict) else None
            if not isinstance(postings, list):
                result.warnings.append("unexpected Workday response shape")
                return result
            for posting in postings:
                if len(result.listings) + result.invalid_count >= max_items:
                    result.warnings.append(f"stopped at max_items={max_items}")
                    return result
                path = posting.get("externalPath") if isinstance(posting, dict) else None
                detail = None
                if path and path not in known and details < detail_budget:
                    details += 1
                    try:
                        detail = await client.get_json(f"{base}{path}")
                    except FetchError:
                        result.warnings.append("a posting's detail could not be fetched")
                self._map(result, source, host, site, posting, detail)
            total = page.get("total") or 0
            offset += len(postings)
            if not postings or offset >= total:
                result.complete = True
                return result
            if list_pages >= max_pages:
                result.warnings.append("stopped at the page limit; removal detection disabled for this run")
                return result
            body["offset"] = offset
            page = await client.post_json(f"{base}/jobs", body)
            result.pages += 1
            list_pages += 1

    def _map(self, result: AdapterResult, source: SourceSnapshot, host: str, site: str, posting: dict, detail: dict | None) -> None:
        if not isinstance(posting, dict):
            result.add_invalid(external_id=None, error=ValueError("posting is not an object"))
            return
        info = (detail or {}).get("jobPostingInfo") or {}
        title = info.get("title") or posting.get("title") or ""
        location = info.get("location") or posting.get("locationsText")
        city, region, country = split_location(location)
        external_path = posting.get("externalPath") or ""
        listing_url = info.get("externalUrl") or f"https://{host}/{site}{external_path}"
        bullet_ids = [b for b in posting.get("bulletFields") or [] if isinstance(b, str)]
        requisition = info.get("jobReqId") or (bullet_ids[0] if bullet_ids else None)
        description = html_to_text(info.get("jobDescription"))
        employment = normalize_employment_type(info.get("timeType"))
        data = {
            "title": title,
            "company": source.organization_name,
            "requisition_id": requisition,
            "location": location,
            "city": city,
            "state_or_region": region,
            "country": match_country(str((info.get("country") or {}).get("descriptor") or "")) or country,
            "work_mode": normalize_work_mode(info.get("remoteType")),
            "employment_type": employment,
            "experience_level": experience_level_from_title(title),
            "description": description,
            "summary": clean_text(description.split("\n\n", 1)[0], max_length=500) if description else None,
            "published_at": parse_datetime(info.get("startDate")) if info.get("startDate") else None,
            "application_url": listing_url,
            "source_url": listing_url,
            "confidence": 0.85 if detail else 0.6,
        }
        kind = classify_job_content_type(title, employment_type=employment)
        # The listing path is present with or without a detail fetch, so the id is stable across syncs.
        external_id = external_path or requisition or None
        if external_id:
            result.seen_ids.add(external_id)
        try:
            record = build_record(kind, {**data, "source_external_id": external_id})
        except ValidationError as exc:
            result.add_invalid(external_id=external_id, error=exc)
            return
        result.listings.append(
            DiscoveredListing(
                record=record,
                raw=trim_raw({"posting": posting, "detail": info}),
                method=self.method,
                evidence={"api": "workday_cxs_public", "external_id": external_id, "source_quality": "OFFICIAL_ATS", "partial_record": detail is None},
            )
        )
