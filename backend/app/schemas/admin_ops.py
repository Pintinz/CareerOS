from datetime import datetime

from pydantic import BaseModel, Field

from app.models.admin_ops import (
    DiscoveredItemStatus,
    DiscoveredItemType,
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


class ContentSourceOut(BaseModel):
    id: str
    name: str
    organization: str | None = None
    url: str
    source_type: SourceType
    country: str | None = None
    industry: str | None = None
    company_id: str | None = None
    is_active: bool
    verification_status: VerificationStatus
    last_checked_at: datetime | None = None
    last_successful_fetch_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    organization: str | None = None
    url: str = Field(min_length=1, max_length=1024)
    source_type: SourceType
    country: str | None = None
    industry: str | None = None
    company_id: str | None = None
    is_active: bool = True


class ContentSourceUpdate(BaseModel):
    name: str | None = None
    organization: str | None = None
    url: str | None = None
    source_type: SourceType | None = None
    country: str | None = None
    industry: str | None = None
    company_id: str | None = None
    is_active: bool | None = None
    verification_status: VerificationStatus | None = None


class DiscoveredItemOut(BaseModel):
    id: str
    source_id: str
    item_type: DiscoveredItemType
    detected_title: str
    detected_company_name: str | None = None
    original_url: str
    status: DiscoveredItemStatus
    created_draft_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoveredItemCreate(BaseModel):
    """Manual "report a discovery" path — used by tests and, until a real ingestion adapter
    exists (see ARCHITECTURE.md), by an editor who spotted something worth tracking by hand."""

    source_id: str
    item_type: DiscoveredItemType
    external_id: str | None = None
    detected_title: str = Field(min_length=1, max_length=500)
    detected_company_name: str | None = None
    original_url: str = Field(min_length=1, max_length=1024)
    raw_payload: dict = {}


class DiscoveryDraftIn(BaseModel):
    """Fields the admin can edit before a draft is created from a discovered item (spec §26) —
    intersects the writable fields of Job/Scholarship/IntelligenceCreate loosely enough to cover
    all three without needing three separate schemas for this one screen."""

    company_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    description: str | None = None
    category: str | None = None  # only meaningful for INTELLIGENCE items.


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
