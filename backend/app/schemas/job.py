from datetime import datetime

from pydantic import BaseModel, Field

from app.models.job import ContentStatus, EmploymentType, ExperienceLevel, SourceType, WorkMode
from app.schemas.company import CompanyOut
from app.schemas.pagination import PaginatedResponse


class JobCompanySummary(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class JobCardOut(BaseModel):
    """Lightweight shape for feed/list rendering (spec §13)."""

    id: str
    slug: str
    title: str
    company: JobCompanySummary
    location: str | None = None
    country: str | None = None
    employment_type: EmploymentType
    work_mode: WorkMode
    experience_level: ExperienceLevel | None = None
    thumbnail_url: str | None = None
    is_featured: bool
    is_urgent: bool
    is_verified: bool
    is_saved: bool = False
    is_demo: bool = False
    published_at: datetime | None = None
    application_deadline: datetime | None = None

    model_config = {"from_attributes": True}


class JobDetailOut(BaseModel):
    """Full shape for the job detail screen (spec §14)."""

    id: str
    slug: str
    title: str
    company: CompanyOut
    location: str | None = None
    city: str | None = None
    country: str | None = None
    employment_type: EmploymentType
    work_mode: WorkMode
    experience_level: ExperienceLevel | None = None
    industry: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    short_summary: str | None = None
    description: str | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None
    preferred_skills: list[str] | None = None
    benefits: list[str] | None = None
    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None
    application_url: str | None = None
    application_email: str | None = None
    application_instructions: str | None = None
    source_type: SourceType
    source_url: str | None = None
    source_published_at: datetime | None = None
    published_at: datetime | None = None
    application_deadline: datetime | None = None
    is_verified: bool
    is_featured: bool
    is_urgent: bool
    is_demo: bool
    is_saved: bool = False

    model_config = {"from_attributes": True}


class JobAdminOut(JobDetailOut):
    is_active: bool
    status: ContentStatus
    expires_at: datetime | None = None
    scheduled_publish_at: datetime | None = None
    created_by_admin_id: str | None = None
    reviewed_by_admin_id: str | None = None
    published_by_admin_id: str | None = None


class JobCreate(BaseModel):
    company_id: str
    title: str = Field(min_length=1, max_length=255)
    location: str | None = None
    city: str | None = None
    country: str | None = None

    employment_type: EmploymentType
    work_mode: WorkMode
    experience_level: ExperienceLevel | None = None
    industry: str | None = None

    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: str | None = None

    short_summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None
    preferred_skills: list[str] | None = None
    benefits: list[str] | None = None

    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None

    application_url: str | None = None
    application_email: str | None = None
    application_instructions: str | None = None

    source_type: SourceType = SourceType.OTHER
    source_url: str | None = None
    source_published_at: datetime | None = None

    application_deadline: datetime | None = None
    expires_at: datetime | None = None
    scheduled_publish_at: datetime | None = None

    is_verified: bool = False
    is_featured: bool = False
    is_urgent: bool = False
    is_active: bool = True
    is_demo: bool = False
    status: ContentStatus = ContentStatus.DRAFT


class JobUpdate(BaseModel):
    company_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = None
    city: str | None = None
    country: str | None = None

    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    experience_level: ExperienceLevel | None = None
    industry: str | None = None

    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: str | None = None

    short_summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None
    preferred_skills: list[str] | None = None
    benefits: list[str] | None = None

    thumbnail_url: str | None = None
    post_image_url: str | None = None
    image_alt_text: str | None = None

    application_url: str | None = None
    application_email: str | None = None
    application_instructions: str | None = None

    source_type: SourceType | None = None
    source_url: str | None = None
    source_published_at: datetime | None = None

    application_deadline: datetime | None = None
    expires_at: datetime | None = None
    scheduled_publish_at: datetime | None = None

    is_verified: bool | None = None
    is_featured: bool | None = None
    is_urgent: bool | None = None
    is_active: bool | None = None
    status: ContentStatus | None = None


class JobListResponse(PaginatedResponse[JobCardOut]):
    pass


class JobAdminListResponse(PaginatedResponse[JobAdminOut]):
    pass
