"""RSS/Atom feeds and schema.org structured data on official pages (spec §24-25).

- `RssAdapter`: company newsrooms, universities, scholarship organizations, industry sources.
  Parsed with defusedxml (no entity expansion, no external entities). Newsroom entries become
  intelligence candidates carrying only the headline, a short summary and the link — never the
  full article body (spec §57). Entries with no career-significant signal are filtered by default
  so routine marketing doesn't flood the review queue (spec §13).
- `StructuredPageAdapter`: official career/scholarship pages that embed schema.org JSON-LD
  (JobPosting, NewsArticle, EducationalOccupationalProgram). Deterministic — no AI. Pages without
  structured data are returned as `unstructured_pages` for an optional research provider.

Neither adapter publishes anything; RSS items always enter the review queue (spec §25).
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from lxml import html as lxml_html
from lxml.etree import ParserError
from pydantic import ValidationError

from app.core.config import Settings
from app.ingestion.adapters.base import AdapterConfigurationError, AdapterResult, DiscoveredListing, SourceAdapter, SourceSnapshot, build_record, trim_raw
from app.ingestion.classification import classify_job_content_type, experience_level_from_title, normalize_employment_type
from app.ingestion.countries import country_name
from app.ingestion.http_client import DiscoveryHttpClient, InvalidResponseError
from app.ingestion.text import clean_text, html_to_text, parse_datetime
from app.ingestion.url_safety import UnsafeUrlError, registrable_domain, validate_public_url

MAX_FEED_ENTRIES = 200
MAX_JSON_LD_BLOCKS = 30
MAX_JSON_LD_CHARS = 500_000

_CATEGORY_RULES: list[tuple[str, re.Pattern]] = [
    ("GRADUATE_RECRUITMENT", re.compile(r"\b(graduate (programme|program|scheme|trainee)|early careers|internship programme)\b", re.I)),
    ("LEADERSHIP", re.compile(r"\b(appoint(s|ed|ment)?|names? .{0,30}(ceo|chief|president|director)|chief executive|new ceo|steps? down|board of directors)\b", re.I)),
    ("ACQUISITION", re.compile(r"\b(acquir(e|es|ed|ing|ition)|merger|takeover|joint venture)\b", re.I)),
    ("PLANT_EXPANSION", re.compile(r"\b(new (plant|facility|factory|refinery|terminal|site)|expan(d|ds|sion) .{0,40}(plant|facility|capacity)|commission(s|ed|ing))\b", re.I)),
    ("AUTOMATION", re.compile(r"\b(automation|automated|robotic|robots?)\b", re.I)),
    ("AI", re.compile(r"\b(artificial intelligence|machine learning|generative ai|\bAI\b)\b")),
    ("INVESTMENTS", re.compile(r"\b(invest(s|ed|ment)|final investment decision|fid|funding round|raises? \$?\d)\b", re.I)),
    ("PROJECTS", re.compile(r"\b(contract (award|win)|awarded .{0,30}contract|project (launch|start|milestone)|first oil|groundbreaking)\b", re.I)),
    ("MANUFACTURING", re.compile(r"\b(manufactur(ing|er)|production line|assembly)\b", re.I)),
    ("ENERGY", re.compile(r"\b(renewable|solar|wind farm|lng|hydrogen|power plant|gas project|oil field)\b", re.I)),
    ("OPERATIONS", re.compile(r"\b(restructur(e|ing)|reorganization|layoffs?|job cuts)\b", re.I)),
    ("TECHNOLOGY", re.compile(r"\b(digital transformation|deploy(s|ed|ment) .{0,30}(system|platform|technology)|technology partnership)\b", re.I)),
    ("HIRING", re.compile(r"\b(hiring|recruit(ing|ment) drive|new jobs|create \d+ jobs)\b", re.I)),
]


# WordPress/CMS feed boilerplate that isn't part of the entry's summary.
_FEED_BOILERPLATE = re.compile(r"\s*The post .{0,300}? appeared first on.*$|\s*\[(?:\.\.\.|…|&hellip;)\]\s*$", re.IGNORECASE | re.DOTALL)


def feed_summary(markup: str | None) -> str | None:
    text = html_to_text(markup, max_length=2_000)
    if not text:
        return None
    return clean_text(_FEED_BOILERPLATE.sub("", text), max_length=500)


def categorize(text: str) -> str | None:
    for category, pattern in _CATEGORY_RULES:
        if pattern.search(text):
            return category
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child_text(element, *names: str) -> str | None:
    for child in element:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return None


def parse_feed(body: bytes) -> list[dict]:
    """Returns [{title, link, id, published, summary, categories}] for RSS 2.0 / RSS 1.0 / Atom."""
    try:
        root = SafeET.fromstring(body)
    except (SafeET.ParseError, DefusedXmlException, ValueError) as exc:
        raise InvalidResponseError("feed is not well-formed or uses forbidden XML features") from exc
    entries = []
    for element in root.iter():
        tag = _local(element.tag)
        if tag not in ("item", "entry"):
            continue
        link = _child_text(element, "link")
        if tag == "entry" or not link:
            for child in element:
                if _local(child.tag) == "link" and child.get("href") and child.get("rel", "alternate") == "alternate":
                    link = child.get("href")
                    break
        entries.append(
            {
                "title": _child_text(element, "title"),
                "link": link,
                "id": _child_text(element, "guid", "id"),
                "published": _child_text(element, "pubDate", "published", "updated", "date"),
                "summary": _child_text(element, "description", "summary"),
                "categories": [c.text.strip() for c in element if _local(c.tag) == "category" and (c.text or "").strip()][:10],
            }
        )
        if len(entries) >= MAX_FEED_ENTRIES:
            break
    return entries


class RssAdapter(SourceAdapter):
    name = "rss"
    method = "RSS"

    def is_enabled(self, settings: Settings) -> bool:
        return settings.rss_discovery_enabled

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        feed_url = source.config("feed_url") or source.url
        response = await client.fetch(feed_url, accept="application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8")
        entries = parse_feed(response.body)
        result = AdapterResult(pages=1, complete=False)  # feeds are rolling windows: absence ≠ removal
        kind = self._content_kind(source)
        include_all = bool(source.config("include_all", False))
        for entry in entries:
            if len(result.listings) + result.invalid_count >= max_items:
                result.warnings.append(f"stopped at max_items={max_items}")
                break
            self._map(result, source, response.url, entry, kind=kind, include_all=include_all)
        return result

    @staticmethod
    def _content_kind(source: SourceSnapshot) -> str:
        types = set(source.content_types)
        if "INTELLIGENCE" in types or source.source_type in ("OFFICIAL_NEWSROOM", "INVESTOR_RELATIONS", "INDUSTRY_PUBLICATION", "NEWS_MEDIA", "REGULATOR"):
            return "INTELLIGENCE"
        if types & {"SCHOLARSHIP", "FELLOWSHIP"} or source.source_type in ("SCHOLARSHIP_PROVIDER", "UNIVERSITY"):
            return "FELLOWSHIP" if types == {"FELLOWSHIP"} else "SCHOLARSHIP"
        return "JOB"

    def _map(self, result: AdapterResult, source: SourceSnapshot, feed_url: str, entry: dict, *, kind: str, include_all: bool) -> None:
        title = clean_text(entry.get("title"), max_length=255)
        link = entry.get("link")
        if link:
            link = urljoin(feed_url, link)
        external_id = (entry.get("id") or link or title or "")[:255] or None
        summary = feed_summary(entry.get("summary"))
        text_for_rules = f"{title or ''} {summary or ''} {' '.join(entry.get('categories') or [])}"
        try:
            if kind == "INTELLIGENCE":
                category = categorize(text_for_rules)
                if category is None and not include_all:
                    result.filtered_count += 1
                    return
                record = build_record("INTELLIGENCE", {
                    "headline": title, "company": source.organization_name, "category": category or "OTHER",
                    "summary": summary, "source_name": source.organization or source.name,
                    "published_at": parse_datetime(entry.get("published")), "source_url": link,
                    "source_external_id": external_id, "confidence": 0.6,
                })
            elif kind in ("SCHOLARSHIP", "FELLOWSHIP"):
                record = build_record(kind, {
                    "name": title, "provider": source.organization_name, "summary": summary,
                    "source_url": link, "source_external_id": external_id, "confidence": 0.55,
                })
            else:
                job_kind = classify_job_content_type(title or "")
                record = build_record(job_kind, {
                    "title": title, "company": source.organization_name, "summary": summary,
                    "experience_level": experience_level_from_title(title or ""),
                    "published_at": parse_datetime(entry.get("published")), "source_url": link,
                    "source_external_id": external_id, "confidence": 0.55,
                })
        except ValidationError as exc:
            result.add_invalid(external_id=external_id, error=exc)
            return
        result.listings.append(
            DiscoveredListing(record=record, raw=trim_raw(entry), method=self.method, evidence={"feed": "rss_atom", "external_id": external_id})
        )


# ------------------------------------------------------------------------------------------------
# schema.org JSON-LD
# ------------------------------------------------------------------------------------------------


def extract_json_ld(markup: str) -> list[dict]:
    """All JSON-LD objects in a page, flattened across @graph and ItemList wrappers."""
    try:
        root = lxml_html.fromstring(markup[:3_000_000])
    except (ParserError, ValueError):
        return []
    objects: list[dict] = []
    for script in root.xpath('//script[@type="application/ld+json"]')[:MAX_JSON_LD_BLOCKS]:
        raw = (script.text or "").strip()
        if not raw or len(raw) > MAX_JSON_LD_CHARS:
            continue
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        stack = [data]
        while stack and len(objects) < 500:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                objects.append(node)
                for key in ("@graph", "itemListElement", "item", "mainEntity"):
                    if key in node:
                        stack.append(node[key])
    return objects


def _types(node: dict) -> set[str]:
    value = node.get("@type")
    return {str(v) for v in value} if isinstance(value, list) else {str(value)} if value else set()


def _text(value) -> str | None:
    if isinstance(value, dict):
        return _text(value.get("name") or value.get("value") or value.get("@value"))
    if isinstance(value, list):
        return ", ".join(t for t in (_text(v) for v in value) if t) or None
    return clean_text(str(value), max_length=500) if value not in (None, "") else None


_SCHEMA_EMPLOYMENT = {
    "FULL_TIME": "FULL_TIME", "PART_TIME": "PART_TIME", "CONTRACTOR": "CONTRACT", "TEMPORARY": "TEMPORARY",
    "INTERN": "INTERNSHIP", "VOLUNTEER": "VOLUNTEER", "PER_DIEM": "TEMPORARY",
}
_SCHEMA_SALARY_UNIT = {"HOUR": "hourly", "DAY": "daily", "WEEK": "weekly", "MONTH": "monthly", "YEAR": "yearly"}


class StructuredPageAdapter(SourceAdapter):
    name = "structured_page"
    method = "STRUCTURED_DATA"
    max_pages = 20

    def is_enabled(self, settings: Settings) -> bool:
        return settings.structured_page_discovery_enabled

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        pages = source.config("pages") or [source.url]
        if not isinstance(pages, list) or not pages:
            raise AdapterConfigurationError("adapter_config.pages must be a list of official page URLs")
        source_domain = registrable_domain(source.url)
        result = AdapterResult()
        for page_url in pages[: self.max_pages]:
            try:
                page_url = validate_public_url(str(page_url))
            except UnsafeUrlError:
                result.warnings.append("skipped an unsafe page URL")
                continue
            if registrable_domain(page_url) != source_domain:
                result.warnings.append("skipped a page outside the source's domain")
                continue
            response = await client.fetch(page_url)
            result.pages += 1
            found = self.extract_into(result, source, response.url, response.text, max_items=max_items)
            if found == 0:
                result.unstructured_pages.append((response.url, response.text))
            if len(result.listings) + result.invalid_count >= max_items:
                result.warnings.append(f"stopped at max_items={max_items}")
                break
        return result

    def extract_into(self, result: AdapterResult, source: SourceSnapshot, page_url: str, markup: str, *, max_items: int = 500) -> int:
        """Deterministic schema.org extraction from one already-fetched page. Returns how many
        structured objects were recognized (0 → the page needs research or manual review)."""
        found = 0
        for node in extract_json_ld(markup):
            if len(result.listings) + result.invalid_count >= max_items:
                break
            types = _types(node)
            if "JobPosting" in types:
                found += 1
                self._job(result, source, page_url, node)
            elif types & {"NewsArticle", "PressRelease", "Article"} and "INTELLIGENCE" in source.content_types:
                found += 1
                self._article(result, source, page_url, node)
        return found

    def _job(self, result: AdapterResult, source: SourceSnapshot, page_url: str, node: dict) -> None:
        title = _text(node.get("title")) or ""
        org = node.get("hiringOrganization") or {}
        locations = node.get("jobLocation") or []
        if isinstance(locations, dict):
            locations = [locations]
        address = (locations[0].get("address") if locations and isinstance(locations[0], dict) else None) or {}
        if isinstance(address, str):
            address = {"streetAddress": address}
        city, region = _text(address.get("addressLocality")), _text(address.get("addressRegion"))
        country = country_name(_text(address.get("addressCountry")))
        location = ", ".join(p for p in (city, region, country) if p) or None
        employment_values = node.get("employmentType") or []
        if isinstance(employment_values, str):
            employment_values = [employment_values]
        employment = next((_SCHEMA_EMPLOYMENT.get(str(v).upper()) for v in employment_values if _SCHEMA_EMPLOYMENT.get(str(v).upper())), None)
        employment = employment or normalize_employment_type(employment_values[0] if employment_values else None)
        work_mode = "REMOTE" if str(node.get("jobLocationType", "")).upper() == "TELECOMMUTE" else "UNSPECIFIED"
        salary = node.get("baseSalary") or {}
        value = salary.get("value") if isinstance(salary, dict) else None
        value = value if isinstance(value, dict) else {}
        identifier = node.get("identifier")
        external_id = _text(identifier) if identifier else None
        valid_through = parse_datetime(node.get("validThrough"))
        description = html_to_text(node.get("description"))
        url = node.get("url") or page_url
        education = node.get("educationRequirements")
        data = {
            "title": title,
            "company": (_text(org.get("name")) if isinstance(org, dict) else _text(org)) or source.organization_name,
            "location": location, "city": city, "state_or_region": region, "country": country,
            "work_mode": work_mode, "employment_type": employment,
            "experience_level": experience_level_from_title(title),
            "industry": _text(node.get("industry")),
            "description": description,
            "summary": clean_text(description.split("\n\n", 1)[0], max_length=500) if description else None,
            "education_requirements": [_text(education)] if education else [],
            "experience_requirements": [_text(node.get("experienceRequirements"))] if node.get("experienceRequirements") else [],
            "preferred_skills": [s.strip() for s in str(_text(node.get("skills")) or "").split(",") if s.strip()][:25],
            "salary_min": _int(value.get("minValue") or value.get("value")),
            "salary_max": _int(value.get("maxValue") or value.get("value")),
            "salary_currency": salary.get("currency") if isinstance(salary, dict) else None,
            "salary_period": _SCHEMA_SALARY_UNIT.get(str(value.get("unitText", "")).upper()),
            "published_at": parse_datetime(node.get("datePosted")),
            # schema.org validThrough is the date the posting closes — the employer's stated deadline.
            "application_deadline": valid_through,
            "expires_at": valid_through,
            "application_url": url,
            "source_url": page_url,
            "confidence": 0.8,
        }
        kind = classify_job_content_type(title, employment_type=employment)
        try:
            record = build_record(kind, {**data, "source_external_id": external_id or url})
        except ValidationError as exc:
            result.add_invalid(external_id=external_id, error=exc)
            return
        result.listings.append(
            DiscoveredListing(record=record, raw=trim_raw(node), method=self.method, evidence={"structured_data": "schema.org/JobPosting", "page": page_url})
        )

    def _article(self, result: AdapterResult, source: SourceSnapshot, page_url: str, node: dict) -> None:
        headline = _text(node.get("headline") or node.get("name"))
        summary = clean_text(_text(node.get("description")), max_length=500)
        category = categorize(f"{headline or ''} {summary or ''}")
        if category is None and not source.config("include_all", False):
            result.filtered_count += 1
            return
        try:
            record = build_record("INTELLIGENCE", {
                "headline": headline, "company": source.organization_name, "category": category or "OTHER",
                "summary": summary, "source_name": source.organization or source.name,
                "published_at": parse_datetime(node.get("datePublished")), "source_url": node.get("url") or page_url,
                "source_external_id": node.get("url") or page_url, "confidence": 0.7,
            })
        except ValidationError as exc:
            result.add_invalid(external_id=None, error=exc)
            return
        result.listings.append(
            DiscoveredListing(record=record, raw=trim_raw(node), method=self.method, evidence={"structured_data": "schema.org/NewsArticle", "page": page_url})
        )


def _int(value) -> int | None:
    try:
        return int(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
