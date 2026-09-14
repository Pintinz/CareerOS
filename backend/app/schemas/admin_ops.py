from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.ingestion.url_safety import UnsafeUrlError, validate_public_url
from app.models.admin_ops import (
    ChangeStatus,
    DiscoveredItemStatus,
    DiscoveredItemType,
    DiscoveryMethod,
    DiscoveryRunStatus,
    DiscoveryRunTrigger,
    DiscoveryRunType,
    ItemVerificationStatus,
    NotificationAudience,
    NotificationStatus,
    SourceType,
    VerificationStatus,
)
from app.schemas.pagination import PaginatedResponse


class AuditLogOut(BaseModel):
    id: str
    admin_id: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    metadata_json: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(PaginatedResponse[AuditLogOut]):
    pass


class SettingOut(BaseModel):
    key: str
    value: dict
    description: str | None = None
    updated_at: datetime | None = None
    is_default: bool


class SettingUpdate(BaseModel):
    value: dict


_CONTENT_TYPES = {t.value for t in DiscoveredItemType}
# Adapter parameters are public identifiers only. Anything that looks like a credential is refused
# so secrets can never end up in the database or the admin UI (spec §28).
_ALLOWED_ADAPTER_KEYS = {
    "company", "board_token", "board_name", "company_identifier", "tenant", "site", "region", "feed_url",
    "pages", "include_all", "search_queries", "allow_ats_domains",
}


def _validate_source_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return validate_public_url(value)
    except UnsafeUrlError as exc:
        raise ValueError(f"Invalid source URL: {exc}") from exc


def _validate_adapter_config(value: dict | None) -> dict | None:
    if value is None:
        return None
    unknown = set(value) - _ALLOWED_ADAPTER_KEYS
    if unknown:
        raise ValueError(f"Unsupported adapter_config keys: {', '.join(sorted(unknown))}")
    for key in ("feed_url",):
        if value.get(key):
            _validate_source_url(str(value[key]))
    pages = value.get("pages")
    if pages is not None:
        if not isinstance(pages, list) or len(pages) > 20:
            raise ValueError("adapter_config.pages must be a list of at most 20 URLs")
        for page in pages:
            _validate_source_url(str(page))
    queries = value.get("search_queries")
    if queries is not None and (not isinstance(queries, list) or len(queries) > 5 or any(len(str(q)) > 200 for q in queries)):
        raise ValueError("adapter_config.search_queries must be at most 5 short queries")
    return value


def _validate_content_types(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    upper = [v.upper() for v in value]
    bad = set(upper) - _CONTENT_TYPES
    if bad:
        raise ValueError(f"Unknown content types: {', '.join(sorted(bad))}")
    return sorted(set(upper))


class ContentSourceOut(BaseModel):
    id: str
    name: str
    organization: str | None = None
    url: str
    domain: str | None = None
    source_type: SourceType
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    company_id: str | None = None
    trust_level: int
    discovery_method: DiscoveryMethod
    content_types: list[str] = []
    adapter_config_json: dict = {}
    is_active: bool
    polling_enabled: bool
    crawl_interval_minutes: int
    auto_publish_allowed: bool
    verification_status: VerificationStatus
    last_checked_at: datetime | None = None
    last_successful_fetch_at: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    last_error_code: str | None = None
    consecutive_failures: int = 0
    next_poll_after: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceHealthOut(ContentSourceOut):
    items_discovered: int = 0
    items_awaiting_review: int = 0
    items_published: int = 0
    last_run_status: DiscoveryRunStatus | None = None
    last_run_at: datetime | None = None
    adapter_available: bool = True


class ContentSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    url: str = Field(min_length=1, max_length=1024)
    source_type: SourceType
    country: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=255)
    company_id: str | None = None
    # None → the registry default for the source type (DISCOVERY_ENGINE.md §Trust levels).
    trust_level: int | None = Field(default=None, ge=1, le=5)
    discovery_method: DiscoveryMethod | None = None
    content_types: list[str] = ["JOB"]
    adapter_config_json: dict = {}
    is_active: bool = True
    polling_enabled: bool = False
    crawl_interval_minutes: int | None = Field(default=None, ge=60, le=10_080)
    auto_publish_allowed: bool = False

    _url = field_validator("url")(classmethod(lambda cls, v: _validate_source_url(v)))
    _adapter = field_validator("adapter_config_json")(classmethod(lambda cls, v: _validate_adapter_config(v)))
    _types = field_validator("content_types")(classmethod(lambda cls, v: _validate_content_types(v)))


class ContentSourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=1024)
    source_type: SourceType | None = None
    country: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=255)
    company_id: str | None = None
    trust_level: int | None = Field(default=None, ge=1, le=5)
    discovery_method: DiscoveryMethod | None = None
    content_types: list[str] | None = None
    adapter_config_json: dict | None = None
    is_active: bool | None = None
    polling_enabled: bool | None = None
    crawl_interval_minutes: int | None = Field(default=None, ge=60, le=10_080)
    auto_publish_allowed: bool | None = None
    verification_status: VerificationStatus | None = None

    _url = field_validator("url")(classmethod(lambda cls, v: _validate_source_url(v)))
    _adapter = field_validator("adapter_config_json")(classmethod(lambda cls, v: _validate_adapter_config(v)))
    _types = field_validator("content_types")(classmethod(lambda cls, v: _validate_content_types(v)))


class DiscoveryRunOut(BaseModel):
    id: str
    source_id: str | None = None
    run_type: DiscoveryRunType
    trigger: DiscoveryRunTrigger
    status: DiscoveryRunStatus
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    items_found: int
    items_new: int
    items_updated: int
    items_duplicate: int
    items_invalid: int
    items_removed: int
    error_code: str | None = None
    error_message: str | None = None
    stats_json: dict = {}

    model_config = {"from_attributes": True}


class DiscoveredItemOut(BaseModel):
    id: str
    source_id: str
    source_name: str | None = None
    item_type: DiscoveredItemType
    detected_title: str
    detected_company_name: str | None = None
    company_id: str | None = None
    original_url: str
    canonical_url: str | None = None
    location: str | None = None
    country: str | None = None
    published_at: datetime | None = None
    deadline: datetime | None = None
    status: DiscoveredItemStatus
    verification_status: ItemVerificationStatus
    trust_level: int | None = None
    confidence: float | None = None
    duplicate_of_id: str | None = None
    matched_entity_type: str | None = None
    matched_entity_id: str | None = None
    created_draft_id: str | None = None
    pending_changes: int = 0
    flags: list[str] = []
    created_at: datetime
    last_seen_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContentChangeOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    field: str
    old_value: object = None
    new_value: object = None
    source_id: str | None = None
    discovered_item_id: str | None = None
    status: ChangeStatus
    detected_at: datetime
    resolved_at: datetime | None = None


class DiscoveryReviewOut(BaseModel):
    """Side-by-side review: what the source said (evidence) vs. what CareerOS would store."""

    item: DiscoveredItemOut
    source: ContentSourceOut
    evidence: dict
    extracted: dict  # normalized record the draft is built from
    raw_payload: dict  # admin-only, bounded
    current_record: dict | None = None  # the existing CareerOS record for updates
    pending_changes: list[ContentChangeOut] = []
    duplicate_of: DiscoveredItemOut | None = None
    can_publish: bool
    publish_blockers: list[str] = []


class DiscoveredItemCreate(BaseModel):
    """Manual "report a discovery" path — an editor who spotted something worth tracking by hand."""

    source_id: str
    item_type: DiscoveredItemType
    external_id: str | None = Field(default=None, max_length=255)
    detected_title: str = Field(min_length=1, max_length=500)
    detected_company_name: str | None = Field(default=None, max_length=255)
    original_url: str = Field(min_length=1, max_length=1024)
    raw_payload: dict = {}

    _url = field_validator("original_url")(classmethod(lambda cls, v: _validate_source_url(v)))


class DiscoveryDraftIn(BaseModel):
    """Admin edits applied before a draft is created or the item is published. Only fields sent
    override the extracted record; the result is re-validated (URLs, lengths, dates)."""

    company_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    category: str | None = None  # INTELLIGENCE only
    location: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=255)
    application_url: str | None = Field(default=None, max_length=1024)
    deadline: datetime | None = None
    career_relevance: str | None = Field(default=None, max_length=1000)


class CompanyProposalIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website_url: str | None = Field(default=None, max_length=1024)
    career_url: str | None = Field(default=None, max_length=1024)
    industry: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=255)
    headquarters: str | None = Field(default=None, max_length=255)

    _website = field_validator("website_url", "career_url")(classmethod(lambda cls, v: _validate_source_url(v) if v else None))


class SourceStateDecisionIn(BaseModel):
    confirm: bool  # True: the listing really is gone/closed → expire it. False: it's still active.


class DiscoveryMetricsOut(BaseModel):
    active_sources: int
    polling_sources: int
    failing_sources: int
    discovery_runs_24h: int
    failed_runs_24h: int
    items_found_24h: int
    items_verified: int
    duplicates_24h: int
    awaiting_review: int
    pending_changes: int
    opportunities_expired_7d: int
    source_removed_pending: int
    average_run_ms_24h: int | None = None
    auto_publish_enabled: bool
    ai_research_available: bool
    flags: dict


class AdminNotificationOut(BaseModel):
    id: str
    title: str
    body: str
    deep_link: str | None = None
    audience: NotificationAudience
    audience_ref_id: str | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    status: NotificationStatus
    recipient_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminNotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=1000)
    deep_link: str | None = None
    audience: NotificationAudience
    audience_ref_id: str | None = None
    scheduled_at: datetime | None = None


class UserAdminOut(BaseModel):
    """Never includes hashed_password, OAuth tokens, CV text, or any other private content (spec
    §30) — this schema simply has no field for any of it."""

    id: str
    email: str
    full_name: str | None = None
    is_active: bool
    is_verified: bool
    applications_tracked: int
    created_at: datetime


class UserAdminListResponse(PaginatedResponse[UserAdminOut]):
    pass
