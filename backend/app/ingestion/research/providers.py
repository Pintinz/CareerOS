"""ResearchProvider abstraction (spec §2, §26, §75-77).

CareerOS never depends on a single AI vendor, and discovery keeps working with none configured:

- `StructuredSourceResearchProvider` — deterministic schema.org extraction from a fetched page.
- `WebResearchProvider` — fetches official candidate URLs itself (robots, SSRF and rate rules via
  DiscoveryHttpClient), tries structured extraction first, and only then an AI provider, within
  budget. Search results are never stored: a URL only yields a record after the backend has
  opened the page and extracted from it (spec §4).
- `AnthropicResearchProvider` (anthropic_provider.py) — AI interpretation of unstructured official
  pages and search-based candidate discovery, when enabled and configured.
- `MockResearchProvider` — deterministic fixtures for tests and local development.

Every provider returns validated `Extracted*` records plus evidence; none can publish.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.ingestion.adapters.base import AdapterResult, SourceSnapshot, build_record
from app.ingestion.adapters.feeds import StructuredPageAdapter
from app.ingestion.http_client import DiscoveryHttpClient, FetchError
from app.ingestion.research.security import (
    AI_CONFIDENCE_CAP,
    INJECTION_CONFIDENCE_CAP,
    EvidenceReport,
    date_supported,
    detect_injection_markers,
    quote_supported,
    title_supported,
    url_allowed,
)
from app.ingestion.schemas import ExtractedJob, ExtractedRecord, ExtractedScholarship, record_title
from app.ingestion.text import html_to_text


class ResearchProviderError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass
class ResearchBudget:
    """Per-run AI spend guard (spec §76). Deterministic providers don't consume it."""

    max_items: int
    max_tokens: int
    min_trust_level: int
    content_types: frozenset[str]
    items_used: int = 0
    tokens_used: int = 0
    skipped: dict = field(default_factory=dict)

    def allows(self, *, source: SourceSnapshot, estimated_tokens: int) -> str | None:
        """None when allowed, else a short reason code."""
        if source.trust_level < self.min_trust_level:
            return "TRUST_BELOW_MINIMUM"
        if self.content_types and source.content_types and not set(source.content_types) & self.content_types:
            return "CONTENT_TYPE_NOT_ENABLED"
        if self.items_used >= self.max_items:
            return "ITEM_BUDGET_EXHAUSTED"
        if self.tokens_used + estimated_tokens > self.max_tokens:
            return "TOKEN_BUDGET_EXHAUSTED"
        return None

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def record(self, tokens: int) -> None:
        self.items_used += 1
        self.tokens_used += tokens


@dataclass
class ResearchRequest:
    source: SourceSnapshot
    page_url: str
    page_text: str  # plain visible text of a page the backend fetched itself
    content_types: tuple[str, ...]


@dataclass
class ResearchOutcome:
    records: list[ExtractedRecord] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)  # parallel to records
    tokens_used: int = 0
    provider: str = ""
    errors: list[str] = field(default_factory=list)
    raw_result: dict = field(default_factory=dict)  # cacheable, validated-shape provider output


class ResearchProvider(ABC):
    name = "base"
    uses_ai = False

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    async def extract(self, request: ResearchRequest) -> ResearchOutcome: ...

    async def discover_candidate_urls(self, *, query: str, allowed_domains: list[str], max_results: int = 5) -> tuple[list[str], int]:
        """(urls, tokens_used). Providers without search return nothing."""
        return [], 0


def apply_evidence_checks(record: ExtractedRecord, *, request: ResearchRequest, quotes: list[str] | None = None) -> tuple[ExtractedRecord | None, EvidenceReport]:
    """Validate an AI-extracted record against the page the backend fetched. Unsupported fields are
    removed; an unsupported title rejects the record."""
    report = EvidenceReport(injection_markers=detect_injection_markers(request.page_text))
    title = record_title(record)
    if not title_supported(title, request.page_text):
        report.passed = False
        report.flags.append("TITLE_NOT_FOUND_ON_PAGE")
        return None, report

    updates: dict = {}
    if isinstance(record, ExtractedJob):
        if not date_supported(record.application_deadline, request.page_text):
            updates["application_deadline"] = None
            updates["expires_at"] = None
            report.dropped_fields.append("application_deadline")
        if not url_allowed(record.application_url, source_url=request.source.url, page_url=request.page_url):
            updates["application_url"] = None
            report.dropped_fields.append("application_url")
            report.flags.append("APPLICATION_URL_OFF_DOMAIN")
    if isinstance(record, ExtractedScholarship):
        if not date_supported(record.deadline, request.page_text):
            updates["deadline"] = None
            report.dropped_fields.append("deadline")
        if not url_allowed(record.official_application_url, source_url=request.source.url, page_url=request.page_url):
            updates["official_application_url"] = None
            report.dropped_fields.append("official_application_url")
            report.flags.append("APPLICATION_URL_OFF_DOMAIN")
    unsupported_quotes = [q for q in (quotes or []) if not quote_supported(q, request.page_text)]
    if unsupported_quotes:
        report.flags.append("QUOTES_NOT_ON_PAGE")

    cap = INJECTION_CONFIDENCE_CAP if report.injection_markers else AI_CONFIDENCE_CAP
    if unsupported_quotes:
        cap = min(cap, 0.5)
    updates["confidence"] = min(record.confidence, cap)
    if report.injection_markers:
        report.flags.append("INJECTION_SUSPECTED")
    return record.model_copy(update=updates), report


class StructuredSourceResearchProvider(ResearchProvider):
    """Deterministic: schema.org JSON-LD in the page markup. Always available, costs nothing."""

    name = "structured"

    def is_available(self) -> bool:
        return True

    async def extract(self, request: ResearchRequest) -> ResearchOutcome:  # page_text must be raw markup here
        result = AdapterResult()
        StructuredPageAdapter().extract_into(result, request.source, request.page_url, request.page_text)
        return ResearchOutcome(
            records=[listing.record for listing in result.listings],
            evidence=[listing.evidence for listing in result.listings],
            provider=self.name,
        )


class MockResearchProvider(ResearchProvider):
    """Returns fixture records (dicts shaped like Extracted* models) — never calls a network. Still
    goes through validation and evidence checks, so tests exercise the real safety path."""

    name = "mock"
    uses_ai = True

    def __init__(self, records_by_url: dict[str, list[dict]] | None = None, *, candidates: dict[str, list[str]] | None = None, tokens_per_call: int = 1000) -> None:
        self.records_by_url = records_by_url or {}
        self.candidates = candidates or {}
        self.tokens_per_call = tokens_per_call
        self.calls: list[str] = []

    def is_available(self) -> bool:
        return True

    async def extract(self, request: ResearchRequest) -> ResearchOutcome:
        self.calls.append(request.page_url)
        outcome = ResearchOutcome(provider=self.name, tokens_used=self.tokens_per_call)
        for fixture in self.records_by_url.get(request.page_url, []):
            raw = dict(fixture)
            quotes = raw.pop("evidence_quotes", None)
            try:
                record = build_record(raw.get("content_type", "JOB"), {**raw, "source_url": raw.get("source_url") or request.page_url})
            except ValidationError as exc:
                outcome.errors.append(f"invalid:{len(exc.errors())}")
                continue
            checked, report = apply_evidence_checks(record, request=request, quotes=quotes)
            if checked is None:
                outcome.errors.append("evidence_rejected")
                continue
            outcome.records.append(checked)
            outcome.evidence.append({"ai_provider": self.name, **report.as_dict()})
        outcome.raw_result = {"records": [r.model_dump(mode="json") for r in outcome.records], "evidence": outcome.evidence}
        return outcome

    async def discover_candidate_urls(self, *, query: str, allowed_domains: list[str], max_results: int = 5) -> tuple[list[str], int]:
        self.calls.append(f"search:{query}")
        return self.candidates.get(query, [])[:max_results], self.tokens_per_call


class WebResearchProvider:
    """Orchestrates research for candidate URLs: fetch (ourselves) → structured → AI (budgeted)."""

    def __init__(self, *, client: DiscoveryHttpClient, ai_provider: ResearchProvider | None, budget: ResearchBudget | None) -> None:
        self.client = client
        self.structured = StructuredSourceResearchProvider()
        self.ai_provider = ai_provider if ai_provider and ai_provider.is_available() else None
        self.budget = budget

    async def research_page(self, source: SourceSnapshot, page_url: str, markup: str | None = None) -> ResearchOutcome:
        if markup is None:
            try:
                response = await self.client.fetch(page_url)
            except FetchError as exc:
                return ResearchOutcome(provider="web", errors=[exc.code])
            page_url, markup = response.url, response.text
        deterministic = await self.structured.extract(ResearchRequest(source=source, page_url=page_url, page_text=markup, content_types=source.content_types))
        if deterministic.records:
            return deterministic
        if self.ai_provider is None or self.budget is None:
            return ResearchOutcome(provider="web", errors=["NO_STRUCTURED_DATA_MANUAL_REVIEW_REQUIRED"])
        text = html_to_text(markup, max_length=None) or ""
        estimated = len(text) // 3 + 4_000
        reason = self.budget.allows(source=source, estimated_tokens=estimated)
        if reason:
            self.budget.skip(reason)
            return ResearchOutcome(provider="web", errors=[f"AI_SKIPPED_{reason}"])
        outcome = await self.ai_provider.extract(ResearchRequest(source=source, page_url=page_url, page_text=text, content_types=source.content_types))
        self.budget.record(outcome.tokens_used or estimated)
        return outcome
