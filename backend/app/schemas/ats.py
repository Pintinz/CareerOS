from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse


class CvDocumentOut(BaseModel):
    id: str
    name: str
    original_filename: str | None = None
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CvDocumentListResponse(PaginatedResponse[CvDocumentOut]):
    pass


class AtsAnalyzeRequest(BaseModel):
    """Exactly one of `cv_document_id`/`cv_text` and exactly one of `job_id`/`job_description`
    must be provided — validated in the service layer where the clearer error message lives."""

    cv_document_id: str | None = None
    cv_text: str | None = Field(default=None, max_length=20_000)
    job_id: str | None = None
    job_description: str | None = Field(default=None, max_length=20_000)
    job_title: str | None = None


class ScoreComponent(BaseModel):
    score: int
    weight: float


class AtsAnalysisOut(BaseModel):
    id: str
    overall_score: int
    score_breakdown: dict[str, ScoreComponent]
    strong_matches: list[str]
    missing_keywords: list[str]
    formatting_issues: list[str]
    missing_metrics_note: str | None = None
    job_id: str | None = None
    job_title: str | None = None
    cv_document_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AtsAnalysisListResponse(PaginatedResponse[AtsAnalysisOut]):
    pass
