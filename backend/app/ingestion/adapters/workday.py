"""Workday public career sites (spec §24 item 5 — "investigate").

Workday-hosted career sites (`{tenant}.wd{N}.myworkdayjobs.com/{site}`) are rendered from a JSON
endpoint the public page itself calls (`/wday/cxs/{tenant}/{site}/jobs`). It is public — no login,
no token — but undocumented and tenant-specific, so this adapter is OFF by default
(WORKDAY_DISCOVERY_ENABLED) and always subject to robots.txt like every other fetch. Postings list
"Posted 3 Days Ago" style dates, so `published_at` is only taken from the detail endpoint's ISO
`startDate` when present, never estimated from the relative label.

SAP SuccessFactors and Oracle Recruiting were investigated and have no single public structured
job-board API across tenants; those sources use the structured-data (JSON-LD) adapter when their
pages embed schema.org JobPosting, or AI research of the official page (DISCOVERY_ENGINE.md).
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
from app.ingestion.http_client import DiscoveryHttpClient
from app.ingestion.text import clean_text, html_to_text, parse_datetime

_HOST = re.compile(r"^(?P<tenant>[a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com$", re.IGNORECASE)
_LOCALE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


class WorkdayAdapter(SourceAdapter):
    name = "workday"
    method = "STRUCTURED_API"
    page_size = 20
    max_pages = 10
    max_detail_fetches = 40

    def is_enabled(self, settings: Settings) -> bool:
        return settings.workday_discovery_enabled

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

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        host, tenant, site = self._site(source)
        base = f"https://{host}/wday/cxs/{quote(tenant)}/{quote(site)}"
        result = AdapterResult()
        offset, details = 0, 0
        for _ in range(self.max_pages):
            page = await client.post_json(f"{base}/jobs", {"appliedFacets": {}, "limit": self.page_size, "offset": offset, "searchText": ""})
            result.pages += 1
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
                if path and details < self.max_detail_fetches:
                    detail = await client.get_json(f"{base}{path}")
                    details += 1
                self._map(result, source, host, site, posting, detail)
            total = page.get("total") or 0
            offset += len(postings)
            if not postings or offset >= total:
                result.complete = True
                return result
        result.warnings.append("stopped at the page limit; removal detection disabled for this run")
        return result

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
            "country": (info.get("country") or {}).get("descriptor") or country,
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
        external_id = info.get("id") or requisition or external_path or None
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
                evidence={"api": "workday_cxs_public", "external_id": external_id, "source_quality": "OFFICIAL_ATS", "experimental": True},
            )
        )
