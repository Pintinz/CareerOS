from datetime import datetime

from pydantic import BaseModel, Field

from app.models.job import ContentStatus, SourceType
from app.models.scholarship import DegreeLevel, FundingType
from app.schemas.pagination import PaginatedResponse


class ScholarshipCardOut(BaseModel):
    """Lightweight shape for the scholarship feed (spec §16)."""

    id: str
    slug: str
    name: str
    organization: str | None = None
    country: str | None = None
    degree_levels: list[str] | None = None
    funding_type: FundingType
    application_deadline: datetime | None = None
    thumbnail_url: str | None = None
    is_verified: bool
    is_featured: bool
    is_saved: bool = False
    is_demo: bool = False

    model_config = {"from_attributes": True}


class ScholarshipDetailOut(BaseModel):
    """Full shape for the scholarship detail screen (spec §17)."""

    id: str
    slug: str
    name: str
    organization: str | None = None
    country: str | None = None
    degree_levels: list[str] | None = None
    fields_of_study: list[str] | None = None
    funding_type: FundingType

    tuition_coverage: str | None = None
    monthly_stipend: str | None = None
    travel_support: str | None = None
    insurance_support: str | None = None
    accommodation_support: str | None = None

    summary: str | None = None
    description: str | None = None

    eligible_nationalities: list[str] | None = None
    academic_requirements: list[str] | None = None
    experience_requirements: list[str] | None = None
    language_requirements: list[str] | None = None
    age_requirement: str | None = None
    required_documents: list[str] | None = None

    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None

    official_url: str | None = None
    source_url: str | None = None
    source_type: SourceType
    source_published_at: datetime | None = None

    application_deadline: datetime | None = None
    published_at: datetime | None = None

    is_verified: bool
    is_featured: bool
    is_demo: bool
    is_saved: bool = False

    model_config = {"from_attributes": True}


class ScholarshipAdminOut(ScholarshipDetailOut):
    is_active: bool
    status: ContentStatus
    scheduled_publish_at: datetime | None = None
    created_by_admin_id: str | None = None
    reviewed_by_admin_id: str | None = None
    published_by_admin_id: str | None = None


class _ScholarshipWritableFields(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    organization: str | None = None
    country: str | None = None
    degree_levels: list[DegreeLevel] | None = None
    fields_of_study: list[str] | None = None
    funding_type: FundingType = FundingType.PARTIAL

    tuition_coverage: str | None = None
    monthly_stipend: str | None = None
    travel_support: str | None = None
    insurance_support: str | None = None
    accommodation_support: str | None = None

    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None

    eligible_nationalities: list[str] | None = None
    academic_requirements: list[str] | None = None
    experience_requirements: list[str] | None = None
    language_requirements: list[str] | None = None
    age_requirement: str | None = None
    required_documents: list[str] | None = None

    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None

    official_url: str | None = None
    source_url: str | None = None
    source_type: SourceType = SourceType.OTHER
    source_published_at: datetime | None = None

    application_deadline: datetime | None = None
    scheduled_publish_at: datetime | None = None

    is_verified: bool = False
    is_featured: bool = False
    is_active: bool = True
    is_demo: bool = False
    status: ContentStatus = ContentStatus.DRAFT


class ScholarshipCreate(_ScholarshipWritableFields):
    pass


class ScholarshipUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    organization: str | None = None
    country: str | None = None
    degree_levels: list[DegreeLevel] | None = None
    fields_of_study: list[str] | None = None
    funding_type: FundingType | None = None

    tuition_coverage: str | None = None
    monthly_stipend: str | None = None
    travel_support: str | None = None
    insurance_support: str | None = None
    accommodation_support: str | None = None

    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None

    eligible_nationalities: list[str] | None = None
    academic_requirements: list[str] | None = None
    experience_requirements: list[str] | None = None
    language_requirements: list[str] | None = None
    age_requirement: str | None = None
    required_documents: list[str] | None = None

    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None

    official_url: str | None = None
    source_url: str | None = None
    source_type: SourceType | None = None
    source_published_at: datetime | None = None

    application_deadline: datetime | None = None
    scheduled_publish_at: datetime | None = None

    is_verified: bool | None = None
    is_featured: bool | None = None
    is_active: bool | None = None
    status: ContentStatus | None = None


class ScholarshipListResponse(PaginatedResponse[ScholarshipCardOut]):
    pass


class ScholarshipAdminListResponse(PaginatedResponse[ScholarshipAdminOut]):
    pass
