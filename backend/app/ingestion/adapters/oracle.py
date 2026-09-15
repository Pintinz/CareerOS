"""Oracle Recruiting Cloud (Oracle Fusion HCM "Candidate Experience") public career sites.

A Candidate Experience site (`https://{pod}.fa.{dc}.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{site}`)
renders from public REST resources the page itself calls — `recruitingCEJobRequisitions` (search)
and `recruitingCEJobRequisitionDetails` (one posting). No login or token; always subject to
robots.txt. Live-verified 2026-09-15 on employer sites including MTN, Emerson, Honeywell,
TotalEnergies and Oracle (CAREER_SOURCE_INTEGRATION.md).

- Country scope: `country_filter` selects the site's own location facets (one request per country),
  so only in-scope requisitions are paged.
- Only the candidate-facing `External*` fields are read; `Internal*` fields are never used.
- `ExternalPostedEndDate` is the date the employer's posting closes and is used as the deadline;
  nothing is estimated when it is absent.
"""

from __future__ import annotations

import re
from urllib.parse import quote, urlsplit

from pydantic import ValidationError

from app.core.config import Settings
from app.ingestion.adapters.base import AdapterConfigurationError, AdapterResult, DiscoveredListing, SourceAdapter, SourceSnapshot, build_record, trim_raw
from app.ingestion.adapters.workday import wanted_countries
from app.ingestion.classification import classify_job_content_type, experience_level_from_title, normalize_employment_type, normalize_work_mode, split_location
from app.ingestion.countries import country_name, match_country
from app.ingestion.http_client import DiscoveryHttpClient, FetchError
from app.ingestion.text import clean_text, html_list_items, html_to_text, parse_datetime, text_lines_as_list

_HOST = re.compile(r"^[a-z0-9-]+\.fa\.[a-z0-9-]+\.oraclecloud\.com$", re.IGNORECASE)
_SITE_IN_PATH = re.compile(r"/sites/([A-Za-z0-9_]+)")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _listing_items(html: str | None) -> list[str]:
    return html_list_items(html) or text_lines_as_list(html_to_text(html))


class OracleRecruitingAdapter(SourceAdapter):
    name = "oracle_recruiting"
    method = "STRUCTURED_API"
    page_size = 25
    max_pages = 10
    max_detail_fetches = 40

    def is_enabled(self, settings: Settings) -> bool:
        return settings.structured_ats_sync_enabled and settings.oracle_recruiting_discovery_enabled

    @staticmethod
    def _site(source: SourceSnapshot) -> tuple[str, str]:
        host = (urlsplit(source.url).hostname or "").lower()
        site = source.config("site_number")
        if not site:
            match = _SITE_IN_PATH.search(urlsplit(source.url).path)
            site = match.group(1) if match else None
        if not (_HOST.match(host) and site and _SAFE_ID.match(site)):
            raise AdapterConfigurationError(
                "use the site's https://{pod}.fa.{dc}.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{site} URL or set site_number"
            )
        return host, site

    def validate_source(self, source: SourceSnapshot) -> None:
        self._site(source)

    def _search_url(self, host: str, site: str, *, offset: int, location_id: str | None) -> str:
        finder = f"findReqs;siteNumber={site},facetsList=LOCATIONS,limit={self.page_size},offset={offset},sortBy=POSTING_DATES_DESC"
        if location_id:
            finder += f",selectedLocationsFacet={location_id}"
        return f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations&finder={finder}"

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        host, site = self._site(source)
        max_pages = source.config("max_pages") or self.max_pages
        detail_budget = [source.config("max_detail_fetches") or self.max_detail_fetches]
        wanted = wanted_countries(source.config("country_filter"))
        result = AdapterResult(complete=True)

        first = await self._page(client, host, site, offset=0, location_id=None)
        result.pages += 1
        scopes: list[str | None] = [None]
        if wanted:
            countries = [
                facet for facet in first.get("locationsFacet") or []
                if isinstance(facet, dict) and "," not in str(facet.get("Name") or "") and match_country(str(facet.get("Name") or "")) in wanted
            ]
            if not countries:
                return result  # the site lists no openings in scope: complete and empty
            scopes = [str(facet["Id"]) for facet in countries if _SAFE_ID.match(str(facet.get("Id") or ""))]

        pages_used = 0
        for scope in scopes:
            page = first if scope is None else await self._page(client, host, site, offset=0, location_id=scope)
            if scope is not None:
                result.pages += 1
            offset = 0
            while True:
                requisitions = page.get("requisitionList")
                if not isinstance(requisitions, list):
                    result.warnings.append("unexpected Oracle Recruiting response shape")
                    result.complete = False
                    return result
                for requisition in requisitions:
                    if len(result.listings) + result.invalid_count >= max_items:
                        result.warnings.append(f"stopped at max_items={max_items}")
                        result.complete = False
                        return result
                    await self._listing(result, source, client, host, site, requisition, detail_budget)
                offset += len(requisitions)
                pages_used += 1
                if not requisitions or offset >= int(page.get("TotalJobsCount") or 0):
                    break
                if pages_used >= max_pages:
                    result.warnings.append("stopped at the page limit; removal detection disabled for this run")
                    result.complete = False
                    return result
                page = await self._page(client, host, site, offset=offset, location_id=scope)
                result.pages += 1
        return result

    async def _page(self, client: DiscoveryHttpClient, host: str, site: str, *, offset: int, location_id: str | None) -> dict:
        data = await client.get_json(self._search_url(host, site, offset=offset, location_id=location_id))
        items = data.get("items") if isinstance(data, dict) else None
        return items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}

    async def _listing(self, result: AdapterResult, source: SourceSnapshot, client: DiscoveryHttpClient, host: str, site: str, requisition, budget: list[int]) -> None:
        if not isinstance(requisition, dict) or not _SAFE_ID.match(str(requisition.get("Id") or "")):
            result.add_invalid(external_id=None, error=ValueError("requisition without a usable id"))
            return
        external_id = str(requisition["Id"])
        result.seen_ids.add(external_id)
        detail = None
        if external_id not in source.known_external_ids and budget[0] > 0:
            budget[0] -= 1
            try:
                data = await client.get_json(
                    f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true"
                    f"&finder=ById;Id=%22{quote(external_id)}%22,siteNumber={site}"
                )
                items = data.get("items") if isinstance(data, dict) else None
                detail = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else None
            except FetchError:
                result.warnings.append("a requisition's detail could not be fetched")
        info = detail or {}
        title = info.get("Title") or requisition.get("Title") or ""
        location = info.get("PrimaryLocation") or requisition.get("PrimaryLocation")
        city, region, country = split_location(location)
        description = html_to_text(info.get("ExternalDescriptionStr")) or clean_text(requisition.get("ShortDescriptionStr"), max_length=2000)
        employment = normalize_employment_type(info.get("JobSchedule") or requisition.get("JobSchedule"))
        skills = [clean_text(s.get("Skill") or s.get("Name"), max_length=80) for s in info.get("skills") or [] if isinstance(s, dict)]
        url = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{quote(external_id)}"
        data = {
            "title": title,
            "company": source.organization_name,
            "requisition_id": external_id,
            "location": location,
            "city": city,
            "state_or_region": region,
            "country": country_name(info.get("PrimaryLocationCountry") or requisition.get("PrimaryLocationCountry")) or country,
            "work_mode": normalize_work_mode(info.get("WorkplaceType") or requisition.get("WorkplaceType")),
            "employment_type": employment,
            "experience_level": experience_level_from_title(title),
            "department": info.get("JobFunction") or requisition.get("JobFunction") or info.get("Department") or requisition.get("Department"),
            "summary": clean_text(requisition.get("ShortDescriptionStr") or info.get("ShortDescriptionStr"), max_length=500),
            "description": description,
            "responsibilities": _listing_items(info.get("ExternalResponsibilitiesStr")),
            "requirements": _listing_items(info.get("ExternalQualificationsStr")),
            "education_requirements": [info["StudyLevel"]] if info.get("StudyLevel") else [],
            "preferred_skills": [s for s in skills if s][:25],
            "published_at": parse_datetime(info.get("ExternalPostedStartDate") or requisition.get("PostedDate")),
            "application_deadline": parse_datetime(info.get("ExternalPostedEndDate") or requisition.get("PostingEndDate")),
            "application_url": url,
            "source_url": url,
            "confidence": 0.85 if detail else 0.6,
        }
        kind = classify_job_content_type(title, employment_type=employment)
        try:
            record = build_record(kind, {**data, "source_external_id": external_id})
        except ValidationError as exc:
            result.add_invalid(external_id=external_id, error=exc)
            return
        result.listings.append(
            DiscoveredListing(
                record=record,
                raw=trim_raw({"requisition": requisition, "detail": {k: v for k, v in info.items() if not str(k).startswith("Internal")}}),
                method=self.method,
                evidence={"api": "oracle_recruiting_ce_public", "external_id": external_id, "source_quality": "OFFICIAL_ATS", "partial_record": detail is None},
            )
        )
