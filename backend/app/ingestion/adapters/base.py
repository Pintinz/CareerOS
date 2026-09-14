"""Source adapter contract. Deterministic adapters come first (spec §24); AI research is only used
where a source offers no structured data (spec §26, §75)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.core.config import Settings
from app.ingestion.http_client import DiscoveryHttpClient
from app.ingestion.schemas import ExtractedIntelligence, ExtractedJob, ExtractedRecord, ExtractedScholarship

MAX_RAW_STRING = 2_000
MAX_INVALID_RECORDED = 25


@dataclass(frozen=True)
class SourceSnapshot:
    """A detached, read-only view of a ContentSource — adapters never touch the ORM session."""

    id: str
    name: str
    organization: str | None
    url: str
    source_type: str
    discovery_method: str
    content_types: tuple[str, ...]
    adapter_config: dict
    trust_level: int
    company_name: str | None = None

    @property
    def organization_name(self) -> str | None:
        return self.company_name or self.organization

    def config(self, key: str, default=None):
        value = self.adapter_config.get(key, default)
        return value.strip() if isinstance(value, str) else value


@dataclass
class DiscoveredListing:
    record: ExtractedRecord
    raw: dict
    method: str
    evidence: dict = field(default_factory=dict)


@dataclass
class AdapterResult:
    listings: list[DiscoveredListing] = field(default_factory=list)
    invalid: list[dict] = field(default_factory=list)
    invalid_count: int = 0
    filtered_count: int = 0
    # True only when the adapter fetched the source's *entire* current listing set — the only case
    # in which a previously seen listing's absence means it was removed at the source.
    complete: bool = False
    # Every external id the source currently lists — including items that failed validation, so a
    # malformed listing is never mistaken for a removed one.
    seen_ids: set[str] = field(default_factory=set)
    pages: int = 0
    warnings: list[str] = field(default_factory=list)
    # Pages that had no structured data; the pipeline may hand these to a research provider.
    unstructured_pages: list[tuple[str, str]] = field(default_factory=list)

    def add_invalid(self, *, external_id: str | None, error: ValidationError | Exception) -> None:
        self.invalid_count += 1
        if external_id:
            self.seen_ids.add(external_id)
        if len(self.invalid) >= MAX_INVALID_RECORDED:
            return
        if isinstance(error, ValidationError):
            # Field locations and error types only — never the offending (untrusted) input values.
            detail = sorted({".".join(str(p) for p in e["loc"]) + f":{e['type']}" for e in error.errors()})[:6]
        else:
            detail = [type(error).__name__]
        self.invalid.append({"external_id": external_id, "errors": detail})


class AdapterConfigurationError(Exception):
    code = "ADAPTER_CONFIG"


class SourceAdapter(ABC):
    name: str = "base"
    method: str = "STRUCTURED_API"

    @abstractmethod
    def is_enabled(self, settings: Settings) -> bool: ...

    @abstractmethod
    async def discover(self, source: SourceSnapshot, client: DiscoveryHttpClient, *, max_items: int) -> AdapterResult: ...


def trim_raw(value, *, depth: int = 0):
    """Bounded copy of a raw payload kept as admin-only evidence."""
    if depth > 4:
        return None
    if isinstance(value, dict):
        return {str(k)[:100]: trim_raw(v, depth=depth + 1) for k, v in list(value.items())[:60]}
    if isinstance(value, list):
        return [trim_raw(v, depth=depth + 1) for v in value[:30]]
    if isinstance(value, str):
        return value if len(value) <= MAX_RAW_STRING else value[:MAX_RAW_STRING] + "…"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:200]


def build_record(kind: str, data: dict) -> ExtractedRecord:
    if kind in ("JOB", "INTERNSHIP", "GRADUATE_PROGRAM"):
        return ExtractedJob.model_validate({**data, "content_type": kind})
    if kind in ("SCHOLARSHIP", "FELLOWSHIP"):
        return ExtractedScholarship.model_validate({**data, "content_type": kind})
    return ExtractedIntelligence.model_validate({**data, "content_type": "INTELLIGENCE"})


def path_segments(url: str) -> list[str]:
    return [segment for segment in urlsplit(url).path.split("/") if segment]
