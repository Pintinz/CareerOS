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
from datetime import datetime, timezone
from urllib.parse import urldefrag, urljoin, urlsplit

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from lxml import html as lxml_html
from lxml.etree import ParserError
from pydantic import ValidationError

from app.core.config import Settings
from app.ingestion.adapters.base import AdapterConfigurationError, AdapterResult, DiscoveredListing, SourceAdapter, SourceSnapshot, build_record, trim_raw
from app.ingestion.classification import classify_job_content_type, experience_level_from_title, normalize_employment_type
from app.ingestion.countries import country_name
from app.ingestion.classification import split_location
from app.ingestion.http_client import DiscoveryHttpClient, FetchError, InvalidResponseError
from app.ingestion.text import clean_text, html_list_items, html_to_text, parse_datetime, text_lines_as_list
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


def extract_microdata(markup: str, *, item_type: str = "JobPosting") -> list[dict]:
    """schema.org microdata (itemscope/itemprop) as JSON-LD-shaped dicts, for sites such as SAP
    SuccessFactors career sites that mark postings up in HTML rather than a JSON-LD block. Only
    attribute values and text are read; `description` keeps its markup for html_to_text."""
    try:
        root = lxml_html.fromstring(markup[:3_000_000])
    except (ParserError, ValueError):
        return []
    scopes = root.xpath(f'//*[@itemscope][contains(@itemtype, "schema.org/{item_type}")]')[:MAX_JSON_LD_BLOCKS]
    return [_microdata_item(scope) for scope in scopes]


def _microdata_item(scope, depth: int = 0) -> dict:
    node: dict = {"@type": (scope.get("itemtype") or "").rstrip("/").rsplit("/", 1)[-1]}
    for element in scope.xpath(".//*[@itemprop]")[:400]:
        owner = element.getparent()
        while owner is not None and owner is not scope and owner.get("itemscope") is None:
            owner = owner.getparent()
        if owner is not scope:
            continue  # belongs to a nested item
        name = element.get("itemprop")
        if element.get("itemscope") is not None and depth < 3:
            value = _microdata_item(element, depth + 1)
        elif element.get("content") is not None:
            value = element.get("content")
        elif element.get("datetime"):
            value = element.get("datetime")
        elif name in ("description", "responsibilities", "qualifications", "experienceRequirements"):
            value = lxml_html.tostring(element, encoding="unicode")[:MAX_JSON_LD_CHARS]
        else:
            value = element.text_content().strip()
        if name and value not in (None, "") and name not in node:
            node[name] = value
    return node


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

# "Application Closing Date: 25th September 2026", "Deadline: September 25, 2026", "Applications close 2026-09-25".
_STATED_CLOSING_DATE = re.compile(
    r"\b(?:application\s+)?(?:closing\s+date|deadline(?:\s+for\s+applications?)?|applications?\s+close[sd]?(?:\s+on)?)"
    r"\s*[:\-–]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9},?\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def stated_closing_date(*texts: str | None) -> datetime | None:
    """A closing date the employer wrote into the posting text, used only when the structured
    data has no `validThrough`. Taken as the end of that day (UTC); anything unparseable → None."""
    for text in texts:
        match = _STATED_CLOSING_DATE.search(text or "")
        if not match:
            continue
        raw = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", match.group(1), flags=re.IGNORECASE).replace(",", "")
        for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%Y-%m-%d"):
            try:
                day = datetime.strptime(raw, fmt)
            except ValueError:
                continue
            return day.replace(hour=23, minute=59, tzinfo=timezone.utc)
    return None


class StructuredPageAdapter(SourceAdapter):
    name = "structured_page"
    method = "STRUCTURED_DATA"
    max_pages = 20
    max_linked_pages = 50

    def is_enabled(self, settings: Settings) -> bool:
        return settings.html_source_sync_enabled and settings.structured_page_discovery_enabled

    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult:
        result = AdapterResult()
        if source.config("sitemap_urls"):
            # Large career sites publish every opening in a sitemap; each opening page carries the data.
            pages, complete = await self._sitemap_pages(source, client, result)
            follow_up = True
        elif source.config("listing_pages"):
            # Careers sites that list openings on one page and publish JobPosting data on each
            # opening's own page (e.g. Flair-hosted boards).
            pages, complete = await self._linked_pages(source, client, result)
            follow_up = True
        else:
            pages = source.config("pages") or [source.url]
            if not isinstance(pages, list) or not pages:
                raise AdapterConfigurationError("adapter_config.pages must be a list of official page URLs")
            pages, complete, follow_up = pages[: self.max_pages], False, False
        source_domain = registrable_domain(source.url)
        for page_url in pages:
            try:
                page_url = validate_public_url(str(page_url))
            except UnsafeUrlError:
                result.warnings.append("skipped an unsafe page URL")
                continue
            if registrable_domain(page_url) != source_domain:
                result.warnings.append("skipped a page outside the source's domain")
                continue
            try:
                response = await client.fetch(page_url)
            except FetchError:
                if not follow_up:
                    raise
                # An opening that closed between listing and fetch shouldn't fail the run, but the
                # listing is then no longer known to be complete.
                result.warnings.append("an opening's page could not be fetched")
                complete = False
                continue
            result.pages += 1
            found = self.extract_into(result, source, response.url, response.text, max_items=max_items)
            if found == 0:
                result.unstructured_pages.append((response.url, response.text))
                complete = False
            if len(result.listings) + result.invalid_count >= max_items:
                result.warnings.append(f"stopped at max_items={max_items}")
                complete = False
                break
        result.complete = complete
        return result

    async def _linked_pages(self, source: SourceSnapshot, client: DiscoveryHttpClient, result: AdapterResult) -> tuple[list[str], bool]:
        listing_pages = source.config("listing_pages")
        marker = source.config("job_link_contains")
        if not isinstance(listing_pages, list) or not marker:
            raise AdapterConfigurationError("adapter_config.listing_pages needs a list of URLs and job_link_contains")
        links: list[str] = []
        source_host = urlsplit(source.url).hostname
        for listing_url in listing_pages[: self.max_pages]:
            try:
                listing_url = validate_public_url(str(listing_url))
            except UnsafeUrlError as exc:
                raise AdapterConfigurationError("adapter_config.listing_pages contains an unsafe URL") from exc
            response = await client.fetch(listing_url)
            result.pages += 1
            # Openings are followed on the listing page's own host or the source's host (an employer's
            # website linking to its hosted board) — never a sibling subdomain on a shared career-site
            # host, which is another employer's board.
            hosts = {urlsplit(response.url).hostname, source_host}
            try:
                root = lxml_html.fromstring(response.text[:3_000_000])
            except (ParserError, ValueError):
                continue
            for href in root.xpath("//a/@href")[:2000]:
                absolute = urldefrag(urljoin(response.url, str(href).strip()))[0]
                parts = urlsplit(absolute)
                if parts.scheme in ("http", "https") and parts.hostname in hosts and marker in parts.path and absolute not in links:
                    links.append(absolute)
        links = self._filtered(source, links)
        # A listing page is only known to show *every* opening when the source says so (e.g. a board that
        # lists all roles on one page). Paginated search results never are, so removal detection stays off.
        complete = bool(source.config("listing_complete", False)) and len(links) <= self.max_linked_pages
        if len(links) > self.max_linked_pages:
            result.warnings.append(f"followed the first {self.max_linked_pages} openings only")
        return links[: self.max_linked_pages], complete

    @staticmethod
    def _filtered(source: SourceSnapshot, links: list[str]) -> list[str]:
        """`link_filters`: keep only opening URLs containing one of these fragments (e.g. "/lagos/"),
        for career sites whose URLs carry the location."""
        fragments = [str(f).lower() for f in source.config("link_filters") or [] if str(f).strip()]
        return [link for link in links if any(f in link.lower() for f in fragments)] if fragments else links

    async def _sitemap_pages(self, source: SourceSnapshot, client: DiscoveryHttpClient, result: AdapterResult) -> tuple[list[str], bool]:
        marker = source.config("job_link_contains")
        sitemaps = source.config("sitemap_urls")
        if not isinstance(sitemaps, list) or not marker:
            raise AdapterConfigurationError("adapter_config.sitemap_urls needs a list of URLs and job_link_contains")
        source_host = urlsplit(source.url).hostname
        entries: list[tuple[str, str]] = []  # (lastmod, url)
        queue = [str(url) for url in sitemaps[:10]]
        fetched = 0
        while queue and fetched < 10:
            try:
                sitemap_url = validate_public_url(queue.pop(0))
            except UnsafeUrlError as exc:
                raise AdapterConfigurationError("adapter_config.sitemap_urls contains an unsafe URL") from exc
            response = await client.fetch(sitemap_url, accept="application/xml, text/xml;q=0.9, */*;q=0.5")
            fetched += 1
            result.pages += 1
            try:
                root = SafeET.fromstring(response.body)
            except (SafeET.ParseError, DefusedXmlException, ValueError) as exc:
                raise InvalidResponseError("sitemap is not well-formed XML") from exc
            hosts = {urlsplit(response.url).hostname, source_host}
            for element in root:
                tag = _local(element.tag)
                loc = _child_text(element, "loc")
                if not loc:
                    continue
                if tag == "sitemap" and len(queue) < 10:
                    queue.append(loc)  # a sitemap index: follow child sitemaps (bounded)
                elif tag == "url":
                    parts = urlsplit(loc)
                    if parts.scheme in ("http", "https") and parts.hostname in hosts and marker in parts.path:
                        entries.append((_child_text(element, "lastmod") or "", loc))
        entries.sort(key=lambda entry: entry[0], reverse=True)  # newest openings first
        links = self._filtered(source, list(dict.fromkeys(url for _, url in entries)))
        complete = len(links) <= self.max_linked_pages and not queue
        if len(links) > self.max_linked_pages:
            result.warnings.append(f"followed the {self.max_linked_pages} most recently updated openings only")
        return links[: self.max_linked_pages], complete

    def extract_into(self, result: AdapterResult, source: SourceSnapshot, page_url: str, markup: str, *, max_items: int = 500) -> int:
        """Deterministic schema.org extraction from one already-fetched page. Returns how many
        structured objects were recognized (0 → the page needs research or manual review)."""
        found = 0
        nodes = extract_json_ld(markup)
        if not any("JobPosting" in _types(node) for node in nodes):
            nodes = nodes + extract_microdata(markup)
        for node in nodes:
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
        place = locations[0] if locations and isinstance(locations[0], dict) else {}
        address = place.get("address") or {}
        if isinstance(address, str):
            address = {"streetAddress": address}
        city, region = _text(address.get("addressLocality")), _text(address.get("addressRegion"))
        country = country_name(_text(address.get("addressCountry")))
        location = ", ".join(p for p in (city, region, country) if p) or None
        street = _text(address.get("streetAddress"))
        if location is None and street:
            # "Lagos, NG" / "Lagos, NG, 101001": a trailing ISO code (before any postcode) is the country.
            parts = [p.strip() for p in street.split(",") if p.strip()]
            while len(parts) > 2 and re.fullmatch(r"[A-Z0-9 -]{3,10}", parts[-1]) and any(ch.isdigit() for ch in parts[-1]):
                parts.pop()
            if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isalpha():
                location = ", ".join(parts[:-1] + [country_name(parts[-1])])
            else:
                location = street
            city, region, country = split_location(location)
        if location is None and _text(place.get("name")):
            # Some boards only name the place ("Port Harcourt"); parse it without inventing a country.
            location = _text(place.get("name"))
            city, region, country = split_location(location)
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
        # schema.org PropertyValue: the id is `value` (`name` names the scheme, e.g. the company).
        external_id = _text(identifier.get("value") or identifier.get("name")) if isinstance(identifier, dict) else _text(identifier)
        description = html_to_text(node.get("description"))
        benefits = html_to_text(node.get("jobBenefits"))
        experience_markup = node.get("experienceRequirements")
        experience_text = html_to_text(experience_markup) if isinstance(experience_markup, str) else _text(experience_markup)
        valid_through = parse_datetime(node.get("validThrough")) or stated_closing_date(description, benefits, experience_text)
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
            "experience_requirements": (html_list_items(experience_markup) if isinstance(experience_markup, str) else []) or text_lines_as_list(experience_text),
            "responsibilities": html_list_items(node.get("responsibilities")) if isinstance(node.get("responsibilities"), str) else [],
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
        result.seen_ids.add(str(external_id or url))
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
