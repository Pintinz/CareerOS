"""Validated, normalized shapes for discovered content (spec §10-13, §18).

Adapters and research providers must produce one of these; nothing else reaches persistence.
Design rules enforced here, not left to callers:
- only facts the source supports: every optional field defaults to None — never a guess;
- text is plain text, whitespace-normalized and length-bounded (HTML never passes through);
- URLs are http(s), credential-free and non-local (`validate_public_url`);
- lists are capped; dates are timezone-aware;
- there is no field for "publish", "status", "approve" or any instruction — a research result
  (or a malicious page steering one) has no way to express a publishing decision.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from app.ingestion.text import clean_text, parse_datetime
from app.ingestion.url_safety import UnsafeUrlError, validate_public_url

ContentTypeLiteral = Literal["JOB", "INTERNSHIP", "GRADUATE_PROGRAM", "SCHOLARSHIP", "FELLOWSHIP", "INTELLIGENCE"]


def _bounded_text(max_length: int):
    def validator(value):
        if value is None:
            return None
        return clean_text(str(value), max_length=max_length)

    return BeforeValidator(validator)


def _url(value):
    if value in (None, ""):
        return None
    try:
        return validate_public_url(str(value))
    except UnsafeUrlError as exc:
        raise ValueError(f"unsafe URL: {exc}") from exc


def _date(value):
    if value in (None, ""):
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError("unrecognized date")
    return parsed


def _string_list(max_items: int = 40, max_item_length: int = 500):
    def validator(value):
        if value in (None, ""):
            return []
        if isinstance(value, str):
            value = [value]
        items = []
        for entry in value:
            text = clean_text(str(entry), max_length=max_item_length) if entry is not None else None
            if text and text not in items:
                items.append(text)
            if len(items) >= max_items:
                break
        return items

    return BeforeValidator(validator)


Title = Annotated[str, _bounded_text(255), Field(min_length=2)]
ShortText = Annotated[str | None, _bounded_text(255)]
Summary = Annotated[str | None, _bounded_text(500)]
LongText = Annotated[str | None, _bounded_text(20_000)]
Url = Annotated[str | None, BeforeValidator(_url)]
RequiredUrl = Annotated[str, BeforeValidator(_url)]
Date = Annotated[datetime | None, BeforeValidator(_date)]
TextList = Annotated[list[str], _string_list()]
ShortList = Annotated[list[str], _string_list(max_items=25, max_item_length=120)]


def _currency(value):
    if value in (None, ""):
        return None
    code = str(value).strip().upper()
    return code if len(code) == 3 and code.isalpha() else None


class _Extracted(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    source_url: RequiredUrl
    source_external_id: Annotated[str | None, _bounded_text(255)] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ExtractedJob(_Extracted):
    content_type: Literal["JOB", "INTERNSHIP", "GRADUATE_PROGRAM"] = "JOB"
    title: Title
    company: ShortText = None
    requisition_id: Annotated[str | None, _bounded_text(255)] = None
    location: ShortText = None
    city: ShortText = None
    state_or_region: ShortText = None
    country: ShortText = None
    work_mode: Literal["ON_SITE", "REMOTE", "HYBRID", "UNSPECIFIED"] = "UNSPECIFIED"
    employment_type: Literal["FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP", "TEMPORARY", "VOLUNTEER"] | None = None
    experience_level: Literal["ENTRY", "JUNIOR", "MID", "SENIOR", "LEAD", "EXECUTIVE"] | None = None
    industry: ShortText = None
    department: ShortText = None
    summary: Summary = None
    description: LongText = None
    responsibilities: TextList = []
    requirements: TextList = []
    preferred_skills: ShortList = []
    education_requirements: TextList = []
    experience_requirements: TextList = []
    salary_min: int | None = Field(default=None, ge=0, le=100_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=100_000_000)
    salary_currency: Annotated[str | None, BeforeValidator(_currency)] = None
    salary_period: Literal["hourly", "daily", "weekly", "monthly", "yearly"] | None = None
    published_at: Date = None
    application_deadline: Date = None
    expires_at: Date = None
    application_url: Url = None
    # Graduate programme / internship specifics (only when the source states them).
    program_duration: ShortText = None
    program_start_date: Date = None
    eligible_degrees: ShortList = []
    eligible_fields: ShortList = []
    graduation_year_requirements: ShortList = []
    age_requirements: ShortText = None

    @model_validator(mode="after")
    def _consistent_salary(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            self.salary_min, self.salary_max = self.salary_max, self.salary_min
        if self.salary_min is None and self.salary_max is None:
            self.salary_currency = None
            self.salary_period = None
        return self


class ExtractedScholarship(_Extracted):
    content_type: Literal["SCHOLARSHIP", "FELLOWSHIP"] = "SCHOLARSHIP"
    name: Title
    provider: ShortText = None
    country: ShortText = None
    degree_levels: ShortList = []
    fields_of_study: ShortList = []
    # FULLY_FUNDED only when the authoritative source says so (checked in `_funding_claim`).
    funding_type: Literal["FULLY_FUNDED", "PARTIAL"] | None = None
    funding_evidence: Annotated[str | None, _bounded_text(500)] = None
    tuition_coverage: ShortText = None
    stipend: ShortText = None
    travel_support: ShortText = None
    insurance_support: ShortText = None
    accommodation_support: ShortText = None
    eligible_nationalities: ShortList = []
    academic_requirements: TextList = []
    experience_requirements: TextList = []
    language_requirements: TextList = []
    age_requirements: ShortText = None
    required_documents: TextList = []
    summary: Summary = None
    description: LongText = None
    opening_date: Date = None
    deadline: Date = None
    official_application_url: Url = None

    @model_validator(mode="after")
    def _funding_claim(self):
        if self.funding_type == "FULLY_FUNDED":
            evidence = (self.funding_evidence or "").lower()
            if "fully funded" not in evidence and "full scholarship" not in evidence and "full funding" not in evidence:
                # A "fully funded" label without the source saying so is dropped, not kept.
                self.funding_type = None
        return self


class ExtractedIntelligence(_Extracted):
    content_type: Literal["INTELLIGENCE"] = "INTELLIGENCE"
    headline: Title
    company: ShortText = None
    category: Literal[
        "LEADERSHIP", "TECHNOLOGY", "AUTOMATION", "INVESTMENTS", "HIRING", "PROJECTS", "ACQUISITION",
        "PLANT_EXPANSION", "MANUFACTURING", "ENERGY", "FINANCE", "AI", "GRADUATE_RECRUITMENT", "OPERATIONS", "OTHER",
    ] = "OTHER"
    # SOURCE FACT: a concise factual summary — never the full article (copyright, spec §57).
    summary: Summary = None
    # CAREER INTERPRETATION: hedged relevance, kept separate from the fact (spec §16).
    career_relevance: Annotated[str | None, _bounded_text(1000)] = None
    relevant_roles: ShortList = []
    relevant_skills: ShortList = []
    source_name: ShortText = None
    published_at: Date = None

    @field_validator("career_relevance")
    @classmethod
    def _no_hiring_claims(cls, value):
        if value is None:
            return value
        lowered = value.lower()
        for claim in (" will hire", " is hiring", " are hiring", " will recruit", " plans to hire"):
            if claim in lowered:
                raise ValueError("career relevance must not assert hiring intent the source didn't state")
        return value


ExtractedRecord = ExtractedJob | ExtractedScholarship | ExtractedIntelligence


def record_title(record: ExtractedRecord) -> str:
    if isinstance(record, ExtractedJob):
        return record.title
    if isinstance(record, ExtractedScholarship):
        return record.name
    return record.headline


def record_organization(record: ExtractedRecord) -> str | None:
    if isinstance(record, ExtractedScholarship):
        return record.provider
    return record.company


def record_canonical_url(record: ExtractedRecord) -> str:
    if isinstance(record, ExtractedJob):
        return record.application_url or record.source_url
    if isinstance(record, ExtractedScholarship):
        return record.official_application_url or record.source_url
    return record.source_url


def record_deadline(record: ExtractedRecord) -> datetime | None:
    if isinstance(record, ExtractedJob):
        return record.application_deadline
    if isinstance(record, ExtractedScholarship):
        return record.deadline
    return None


def record_published_at(record: ExtractedRecord) -> datetime | None:
    if isinstance(record, (ExtractedJob, ExtractedIntelligence)):
        return record.published_at
    return record.opening_date


def parse_record(data: dict) -> ExtractedRecord:
    """Validate a stored/untrusted dict back into the right model by its content_type."""
    content_type = str(data.get("content_type", "")).upper()
    if content_type in ("JOB", "INTERNSHIP", "GRADUATE_PROGRAM"):
        return ExtractedJob.model_validate(data)
    if content_type in ("SCHOLARSHIP", "FELLOWSHIP"):
        return ExtractedScholarship.model_validate(data)
    if content_type == "INTELLIGENCE":
        return ExtractedIntelligence.model_validate(data)
    raise ValueError(f"unknown content_type '{content_type}'")

