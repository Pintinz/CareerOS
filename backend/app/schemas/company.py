from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse


class CompanyOut(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: str | None = None
    banner_url: str | None = None
    website_url: str | None = None
    career_url: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    country: str | None = None
    description: str | None = None
    known_technologies: list[str] | None = None
    business_areas: list[str] | None = None
    locations: list[str] | None = None
    is_verified: bool
    is_active: bool
    is_demo: bool = False
    is_following: bool = False

    model_config = {"from_attributes": True}


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    logo_url: str | None = None
    banner_url: str | None = None
    website_url: str | None = None
    career_url: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    country: str | None = None
    description: str | None = None
    known_technologies: list[str] | None = None
    business_areas: list[str] | None = None
    locations: list[str] | None = None
    is_verified: bool = False
    is_active: bool = True
    is_demo: bool = False


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    logo_url: str | None = None
    banner_url: str | None = None
    website_url: str | None = None
    career_url: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    country: str | None = None
    description: str | None = None
    known_technologies: list[str] | None = None
    business_areas: list[str] | None = None
    locations: list[str] | None = None
    is_verified: bool | None = None
    is_active: bool | None = None
    is_demo: bool | None = None


class CompanyListResponse(PaginatedResponse[CompanyOut]):
    pass
