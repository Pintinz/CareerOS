from datetime import datetime

from pydantic import BaseModel, Field

from app.models.intelligence_post import IntelligenceCategory
from app.models.job import ContentStatus, SourceType
from app.schemas.job import JobCompanySummary
from app.schemas.pagination import PaginatedResponse


class IntelligenceCardOut(BaseModel):
    id: str
    slug: str
    headline: str
    category: IntelligenceCategory
    company: JobCompanySummary | None = None
    thumbnail_url: str | None = None
    # Short dek for feed cards (Phase UI restructure) — already stored on the post, max 500 chars.
    summary: str | None = None
    published_at: datetime | None = None
    is_featured: bool

    model_config = {"from_attributes": True}


class IntelligenceDetailOut(BaseModel):
    id: str
    slug: str
    headline: str
    category: IntelligenceCategory
    company: JobCompanySummary | None = None
    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None
    summary: str | None = None
    full_content: str | None = None
    why_it_matters: str | None = None
    relevant_roles: list[str] | None = None
    relevant_skills: list[str] | None = None
    source_type: SourceType
    source_url: str | None = None
    source_published_at: datetime | None = None
    published_at: datetime | None = None
    is_verified: bool
    is_featured: bool
    is_demo: bool

    model_config = {"from_attributes": True}


class IntelligenceAdminOut(IntelligenceDetailOut):
    is_active: bool
    status: ContentStatus
    scheduled_publish_at: datetime | None = None
    created_by_admin_id: str | None = None
    reviewed_by_admin_id: str | None = None
    published_by_admin_id: str | None = None
    company_id: str | None = None


class _IntelligenceWritableFields(BaseModel):
    company_id: str | None = None
    headline: str = Field(min_length=1, max_length=255)
    category: IntelligenceCategory
    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None
    summary: str | None = Field(default=None, max_length=500)
    full_content: str | None = None
    why_it_matters: str | None = None
    relevant_roles: list[str] | None = None
    relevant_skills: list[str] | None = None
    source_type: SourceType = SourceType.OTHER
    source_url: str | None = None
    source_published_at: datetime | None = None
    is_verified: bool = False
    is_featured: bool = False
    is_active: bool = True
    is_demo: bool = False
    status: ContentStatus = ContentStatus.DRAFT
    scheduled_publish_at: datetime | None = None


class IntelligenceCreate(_IntelligenceWritableFields):
    pass


class IntelligenceUpdate(BaseModel):
    company_id: str | None = None
    headline: str | None = Field(default=None, min_length=1, max_length=255)
    category: IntelligenceCategory | None = None
    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None
    summary: str | None = Field(default=None, max_length=500)
    full_content: str | None = None
    why_it_matters: str | None = None
    relevant_roles: list[str] | None = None
    relevant_skills: list[str] | None = None
    source_type: SourceType | None = None
    source_url: str | None = None
    source_published_at: datetime | None = None
    is_verified: bool | None = None
    is_featured: bool | None = None
    is_active: bool | None = None
    status: ContentStatus | None = None
    scheduled_publish_at: datetime | None = None


class IntelligenceListResponse(PaginatedResponse[IntelligenceCardOut]):
    pass


class IntelligenceAdminListResponse(PaginatedResponse[IntelligenceAdminOut]):
    pass
