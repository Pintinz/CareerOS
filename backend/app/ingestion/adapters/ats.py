"""Public ATS job-board adapters (spec §24): Lever, Greenhouse, Ashby, SmartRecruiters.

Each reads the provider's documented public job-board API — the same data the employer publishes
on its hosted careers site — so no AI is needed to interpret it (spec §24: "do not use AI to parse
data already provided cleanly by a structured source"). Only fields the API returns are mapped;
salary, deadline and work mode stay empty/UNSPECIFIED when absent.
"""

from __future__ import annotations

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
    normalize_salary_period,
    normalize_work_mode,
    split_location,
)
from app.ingestion.countries import country_name
from app.ingestion.http_client import DiscoveryHttpClient
from app.ingestion.text import clean_text, html_list_items, html_to_text, parse_datetime, text_lines_as_list


def _summary_from(text: str | None) -> str | None:
    if not text:
        return None
    first_paragraph = text.strip().split("\n\n", 1)[0]
    return clean_text(first_paragraph, max_length=500)


def _identifier(source: SourceSnapshot, *, config_key: str, hosts: tuple[str, ...], api_prefix: tuple[str, ...] = ()) -> str:
    configured = source.config(config_key)
    if configured:
        return configured
    parts = urlsplit(source.url)
    host = (parts.hostname or "").lower()
    segments = path_segments(source.url)
    if any(host == h or host.endswith("." + h) for h in hosts) and segments:
        # Skip API path prefixes like /v0/postings/{id} or /v1/boards/{token}.
        remaining = segments
        for prefix in api_prefix:
            if remaining and remaining[0] == prefix:
                remaining = remaining[1:]
        if remaining:
            return remaining[0]
    raise AdapterConfigurationError(f"set adapter_config.{config_key} or use the provider's public board URL")


class _AtsAdapter(SourceAdapter):
    method = "STRUCTURED_API"
    api_label = "ats"

    def _listing(self, result: AdapterResult, *, source: SourceSnapshot, raw: dict, data: dict, external_id: str | None) -> None:
        employment = data.get("employment_type")
        kind = classify_job_content_type(data.get("title") or "", employment_type=employment)
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
                raw=trim_raw(raw),
                method=self.method,
                evidence={"api": self.api_label, "external_id": external_id, "source_quality": "OFFICIAL_ATS"},
            )
        )


class LeverAdapter(_AtsAdapter):
    name = "lever"
    api_label = "lever_postings_v0"
    page_size = 100

    def is_enabled(self, settings: Settings) -> bool:
        return settings.lever_discovery_enabled

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        site = _identifier(source, config_key="company", hosts=("lever.co",), api_prefix=("v0", "postings"))
        api_host = "api.eu.lever.co" if (source.config("region") == "eu" or ".eu." in source.url) else "api.lever.co"
        result = AdapterResult()
        skip = 0
        while True:
            postings = await client.get_json(
                f"https://{api_host}/v0/postings/{quote(site)}", params={"mode": "json", "skip": skip, "limit": self.page_size}
            )
            result.pages += 1
            if not isinstance(postings, list):
                result.warnings.append("unexpected Lever response shape")
                return result
            for posting in postings:
                if len(result.listings) + result.invalid_count >= max_items:
                    result.warnings.append(f"stopped at max_items={max_items}")
                    return result
                self._map(result, source, posting)
            if len(postings) < self.page_size:
                result.complete = True
                return result
            skip += self.page_size

    def _map(self, result: AdapterResult, source: SourceSnapshot, posting: dict) -> None:
        if not isinstance(posting, dict):
            result.add_invalid(external_id=None, error=ValueError("posting is not an object"))
            return
        categories = posting.get("categories") or {}
        title = posting.get("text") or ""
        description = posting.get("descriptionPlain") or html_to_text(posting.get("description"))
        requirements, responsibilities = [], []
        for section in posting.get("lists") or []:
            heading = (section.get("text") or "").lower()
            items = html_list_items(section.get("content"))
            if any(word in heading for word in ("require", "qualif", "you have", "what you bring", "skills")):
                requirements.extend(items)
            elif any(word in heading for word in ("responsib", "you will", "what you'll do", "day to day", "role")):
                responsibilities.extend(items)
        location = categories.get("location")
        city, region, country_from_location = split_location(location)
        salary = posting.get("salaryRange") or {}
        employment = normalize_employment_type(categories.get("commitment"))
        data = {
            "title": title,
            "company": source.organization_name,
            "location": location,
            "city": city,
            "state_or_region": region,
            "country": country_name(posting.get("country")) or country_from_location,
            "work_mode": normalize_work_mode(posting.get("workplaceType")),
            "employment_type": employment,
            "experience_level": experience_level_from_title(title),
            "department": categories.get("department") or categories.get("team"),
            "description": description,
            "summary": _summary_from(description),
            "requirements": requirements,
            "responsibilities": responsibilities,
            "salary_min": salary.get("min"),
            "salary_max": salary.get("max"),
            "salary_currency": salary.get("currency"),
            "salary_period": normalize_salary_period(salary.get("interval")),
            "published_at": parse_datetime(posting.get("createdAt")),
            "application_url": posting.get("applyUrl") or posting.get("hostedUrl"),
            "source_url": posting.get("hostedUrl") or posting.get("applyUrl"),
            "confidence": 0.9,
        }
        self._listing(result, source=source, raw=posting, data=data, external_id=str(posting.get("id")) if posting.get("id") else None)


class GreenhouseAdapter(_AtsAdapter):
    name = "greenhouse"
    api_label = "greenhouse_job_board_v1"

    def is_enabled(self, settings: Settings) -> bool:
        return settings.greenhouse_discovery_enabled

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        token = _identifier(source, config_key="board_token", hosts=("greenhouse.io",), api_prefix=("v1", "boards"))
        payload = await client.get_json(f"https://boards-api.greenhouse.io/v1/boards/{quote(token)}/jobs", params={"content": "true"})
        result = AdapterResult(pages=1)
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            result.warnings.append("unexpected Greenhouse response shape")
            return result
        for job in jobs:
            if len(result.listings) + result.invalid_count >= max_items:
                result.warnings.append(f"stopped at max_items={max_items}")
                return result
            self._map(result, source, job)
        result.complete = True  # the job board endpoint returns every open job in one response
        return result

    def _map(self, result: AdapterResult, source: SourceSnapshot, job: dict) -> None:
        if not isinstance(job, dict):
            result.add_invalid(external_id=None, error=ValueError("job is not an object"))
            return
        title = job.get("title") or ""
        location = (job.get("location") or {}).get("name")
        city, region, country = split_location(location)
        content_html = job.get("content")
        description = html_to_text(content_html)
        departments = [d.get("name") for d in job.get("departments") or [] if isinstance(d, dict) and d.get("name")]
        work_mode = normalize_work_mode(location) if location and location.strip().lower() in ("remote", "hybrid") else "UNSPECIFIED"
        data = {
            "title": title,
            "company": source.organization_name,
            "requisition_id": job.get("requisition_id"),
            "location": location,
            "city": city,
            "state_or_region": region,
            "country": country,
            "work_mode": work_mode,
            "experience_level": experience_level_from_title(title),
            "department": departments[0] if departments else None,
            "description": description,
            "summary": _summary_from(description),
            "published_at": parse_datetime(job.get("first_published") or job.get("updated_at")),
            "application_url": job.get("absolute_url"),
            "source_url": job.get("absolute_url"),
            "confidence": 0.9,
        }
        self._listing(result, source=source, raw=job, data=data, external_id=str(job.get("id")) if job.get("id") else None)


class AshbyAdapter(_AtsAdapter):
    name = "ashby"
    api_label = "ashby_posting_api"

    _EMPLOYMENT = {"FullTime": "FULL_TIME", "PartTime": "PART_TIME", "Intern": "INTERNSHIP", "Contract": "CONTRACT", "Temporary": "TEMPORARY"}
    _WORKPLACE = {"OnSite": "ON_SITE", "Remote": "REMOTE", "Hybrid": "HYBRID"}

    def is_enabled(self, settings: Settings) -> bool:
        return settings.ashby_discovery_enabled

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        board = _identifier(source, config_key="board_name", hosts=("ashbyhq.com",), api_prefix=("posting-api", "job-board"))
        payload = await client.get_json(
            f"https://api.ashbyhq.com/posting-api/job-board/{quote(board)}", params={"includeCompensation": "true"}
        )
        result = AdapterResult(pages=1)
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            result.warnings.append("unexpected Ashby response shape")
            return result
        for job in jobs:
            if len(result.listings) + result.invalid_count >= max_items:
                result.warnings.append(f"stopped at max_items={max_items}")
                return result
            if isinstance(job, dict) and job.get("isListed") is False:
                result.filtered_count += 1
                continue
            self._map(result, source, job)
        result.complete = True
        return result

    def _map(self, result: AdapterResult, source: SourceSnapshot, job: dict) -> None:
        if not isinstance(job, dict):
            result.add_invalid(external_id=None, error=ValueError("job is not an object"))
            return
        title = job.get("title") or ""
        address = ((job.get("address") or {}).get("postalAddress")) or {}
        description = job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml"))
        work_mode = self._WORKPLACE.get(job.get("workplaceType") or "", "REMOTE" if job.get("isRemote") is True else "UNSPECIFIED")
        salary_min = salary_max = currency = period = None
        for component in ((job.get("compensation") or {}).get("summaryComponents") or []):
            if isinstance(component, dict) and component.get("compensationType") == "Salary":
                salary_min, salary_max = component.get("minValue"), component.get("maxValue")
                currency = component.get("currencyCode")
                interval = (component.get("interval") or "").upper()
                period = {"1 YEAR": "yearly", "1 MONTH": "monthly", "1 WEEK": "weekly", "1 DAY": "daily", "1 HOUR": "hourly"}.get(interval)
                break
        job_url = job.get("jobUrl")
        external_id = job.get("id") or (path_segments(job_url)[-1] if job_url else None)
        data = {
            "title": title,
            "company": source.organization_name,
            "location": job.get("location"),
            "city": address.get("addressLocality"),
            "state_or_region": address.get("addressRegion"),
            "country": country_name(address.get("addressCountry")),
            "work_mode": work_mode,
            "employment_type": self._EMPLOYMENT.get(job.get("employmentType") or ""),
            "experience_level": experience_level_from_title(title),
            "department": job.get("department") or job.get("team"),
            "description": description,
            "summary": _summary_from(description),
            "salary_min": int(salary_min) if isinstance(salary_min, (int, float)) else None,
            "salary_max": int(salary_max) if isinstance(salary_max, (int, float)) else None,
            "salary_currency": currency,
            "salary_period": period,
            "published_at": parse_datetime(job.get("publishedAt")),
            "application_url": job.get("applyUrl") or job_url,
            "source_url": job_url or job.get("applyUrl"),
            "confidence": 0.9,
        }
        self._listing(result, source=source, raw=job, data=data, external_id=str(external_id) if external_id else None)


class SmartRecruitersAdapter(_AtsAdapter):
    name = "smartrecruiters"
    api_label = "smartrecruiters_posting_api_v1"
    page_size = 100
    max_detail_fetches = 40

    _EXPERIENCE = {"entry_level": "ENTRY", "internship": "ENTRY", "associate": "JUNIOR", "director": "EXECUTIVE", "executive": "EXECUTIVE"}

    def is_enabled(self, settings: Settings) -> bool:
        return settings.smartrecruiters_discovery_enabled

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        company = _identifier(source, config_key="company_identifier", hosts=("smartrecruiters.com",), api_prefix=("v1", "companies"))
        base = f"https://api.smartrecruiters.com/v1/companies/{quote(company)}/postings"
        result = AdapterResult()
        offset, details_fetched = 0, 0
        while True:
            page = await client.get_json(base, params={"limit": self.page_size, "offset": offset})
            result.pages += 1
            content = page.get("content") if isinstance(page, dict) else None
            if not isinstance(content, list):
                result.warnings.append("unexpected SmartRecruiters response shape")
                return result
            for summary in content:
                if len(result.listings) + result.invalid_count >= max_items:
                    result.warnings.append(f"stopped at max_items={max_items}")
                    return result
                detail = None
                posting_id = summary.get("id") if isinstance(summary, dict) else None
                if posting_id and details_fetched < self.max_detail_fetches:
                    detail = await client.get_json(f"{base}/{quote(str(posting_id))}")
                    details_fetched += 1
                self._map(result, source, company, summary, detail)
            total = page.get("totalFound") or 0
            offset += len(content)
            if not content or offset >= total:
                # Every posting id was listed (details may be capped, ids are not).
                result.complete = offset >= total
                return result

    def _map(self, result: AdapterResult, source: SourceSnapshot, company: str, summary: dict, detail: dict | None) -> None:
        if not isinstance(summary, dict):
            result.add_invalid(external_id=None, error=ValueError("posting is not an object"))
            return
        posting = {**summary, **(detail or {})}
        title = posting.get("name") or ""
        location = posting.get("location") or {}
        sections = ((posting.get("jobAd") or {}).get("sections")) or {}
        description_text = html_to_text((sections.get("jobDescription") or {}).get("text"))
        qualifications = (sections.get("qualifications") or {}).get("text")
        requirements = html_list_items(qualifications) or text_lines_as_list(html_to_text(qualifications))
        if location.get("remote") is True:
            work_mode = "REMOTE"
        elif location.get("hybrid") is True:
            work_mode = "HYBRID"
        else:
            work_mode = "UNSPECIFIED"
        experience_id = ((posting.get("experienceLevel") or {}).get("id") or "").lower()
        employment = normalize_employment_type((posting.get("typeOfEmployment") or {}).get("label"))
        if experience_id == "internship":
            employment = "INTERNSHIP"
        city = location.get("city")
        data = {
            "title": title,
            "company": (posting.get("company") or {}).get("name") or source.organization_name,
            "requisition_id": posting.get("refNumber"),
            "location": location.get("fullLocation") or ", ".join(p for p in (city, country_name(location.get("country"))) if p) or None,
            "city": city,
            "state_or_region": location.get("region"),
            "country": country_name(location.get("country")),
            "work_mode": work_mode,
            "employment_type": employment,
            "experience_level": self._EXPERIENCE.get(experience_id) or experience_level_from_title(title),
            "industry": (posting.get("industry") or {}).get("label"),
            "department": (posting.get("department") or {}).get("label") or (posting.get("function") or {}).get("label"),
            "description": description_text,
            "summary": _summary_from(description_text),
            "requirements": requirements,
            "published_at": parse_datetime(posting.get("releasedDate")),
            "application_url": posting.get("applyUrl") or posting.get("postingUrl"),
            "source_url": posting.get("postingUrl") or posting.get("applyUrl")
            or f"https://jobs.smartrecruiters.com/{quote(company)}/{quote(str(posting.get('id', '')))}",
            "confidence": 0.9 if detail else 0.7,
        }
        self._listing(result, source=source, raw=posting, data=data, external_id=str(posting.get("id")) if posting.get("id") else None)
