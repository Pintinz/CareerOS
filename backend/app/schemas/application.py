from datetime import datetime

from pydantic import BaseModel, Field

from app.models.application import ApplicationStage
from app.schemas.pagination import PaginatedResponse


class ApplicationStageEventOut(BaseModel):
    id: str
    stage: ApplicationStage
    occurred_at: datetime
    note: str | None = None
    source: str

    model_config = {"from_attributes": True}


class ApplicationNoteOut(BaseModel):
    id: str
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    id: str
    job_id: str | None = None
    cv_document_id: str | None = None
    company_name: str
    role_title: str
    location: str | None = None
    job_url: str | None = None
    current_stage: ApplicationStage
    applied_date: datetime | None = None
    deadline: datetime | None = None
    interview_date: datetime | None = None
    assessment_date: datetime | None = None
    salary: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    cover_letter_text: str | None = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationDetailOut(ApplicationOut):
    timeline: list[ApplicationStageEventOut] = []
    notes: list[ApplicationNoteOut] = []


class ApplicationCreate(BaseModel):
    job_id: str | None = None
    # Required when job_id isn't given (manual entry) — validated in the service layer where a
    # combined error message is clearer than per-field pydantic errors for this either/or case.
    company_name: str | None = Field(default=None, max_length=255)
    role_title: str | None = Field(default=None, max_length=255)
    location: str | None = None
    job_url: str | None = None
    cv_document_id: str | None = None
    current_stage: ApplicationStage = ApplicationStage.SAVED
    applied_date: datetime | None = None
    deadline: datetime | None = None
    salary: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    cover_letter_text: str | None = None


class ApplicationUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=255)
    role_title: str | None = Field(default=None, max_length=255)
    location: str | None = None
    job_url: str | None = None
    cv_document_id: str | None = None
    applied_date: datetime | None = None
    deadline: datetime | None = None
    interview_date: datetime | None = None
    assessment_date: datetime | None = None
    salary: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    cover_letter_text: str | None = None


class ApplicationStageUpdate(BaseModel):
    stage: ApplicationStage
    note: str | None = None
    occurred_at: datetime | None = None  # defaults to now — lets a user backdate an update


class ApplicationNoteCreate(BaseModel):
    text: str = Field(min_length=1)


class ApplicationListResponse(PaginatedResponse[ApplicationOut]):
    pass
