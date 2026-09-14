"""Mapping between validated discovery records and CareerOS content rows, and field-level diffs.

A draft/published row carries exactly the facts the record holds — enum fields the source didn't
state become UNSPECIFIED, never a plausible guess (DISCOVERY_ENGINE.md, "never invent data").
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.ingestion.schemas import ExtractedIntelligence, ExtractedJob, ExtractedRecord, ExtractedScholarship
from app.ingestion.text import content_hash, normalize_title
from app.ingestion.url_safety import canonicalize_url
from app.models.admin_ops import ContentSource, DiscoveredItemType
from app.models.intelligence_post import IntelligenceCategory, IntelligencePost
from app.models.job import (
    ContentStatus,
    EmploymentType,
    ExperienceLevel,
    Job,
    OpportunityType,
    SourceState,
    SourceType,
    WorkMode,
)
from app.models.scholarship import AwardType, FundingType, Scholarship

ENTITY_JOB = "JOB"
ENTITY_SCHOLARSHIP = "SCHOLARSHIP"
ENTITY_INTELLIGENCE = "INTELLIGENCE"

SOURCE_QUALITY_LABELS = {
    "OFFICIAL_CAREER_PAGE": "Official employer careers page",
    "OFFICIAL_NEWSROOM": "Official company newsroom",
    "INVESTOR_RELATIONS": "Official investor relations",
    "GOVERNMENT": "Government portal",
    "REGULATOR": "Regulator",
    "UNIVERSITY": "University website",
    "SCHOLARSHIP_PROVIDER": "Official scholarship provider",
    "GREENHOUSE": "Official ATS (Greenhouse)",
    "LEVER": "Official ATS (Lever)",
    "ASHBY": "Official ATS (Ashby)",
    "SMARTRECRUITERS": "Official ATS (SmartRecruiters)",
    "WORKDAY": "Official ATS (Workday)",
    "SUCCESSFACTORS": "Official ATS (SAP SuccessFactors)",
    "ORACLE": "Official ATS (Oracle Recruiting)",
    "RSS": "RSS feed",
    "INDUSTRY_PUBLICATION": "Industry publication",
    "NEWS_MEDIA": "News organization",
    "AGGREGATOR": "Discovery-only aggregator",
    "OTHER": "Other source",
}


def entity_type_for(item_type: DiscoveredItemType | str) -> str:
    value = item_type.value if isinstance(item_type, DiscoveredItemType) else str(item_type)
    if value in ("JOB", "INTERNSHIP", "GRADUATE_PROGRAM"):
        return ENTITY_JOB
    if value in ("SCHOLARSHIP", "FELLOWSHIP"):
        return ENTITY_SCHOLARSHIP
    return ENTITY_INTELLIGENCE


def record_hash(record: ExtractedRecord) -> str:
    data = record.model_dump(mode="json", exclude={"confidence", "source_external_id"})
    return content_hash(sorted(data.items()))


def _enum(enum_cls, value, default):
    try:
        return enum_cls(value) if value else default
    except ValueError:
        return default


def _nonempty(value):
    return value if value not in (None, [], {}, "") else None


def job_fields(record: ExtractedJob) -> dict:
    eligibility = {
        key: value
        for key, value in {
            "eligible_degrees": record.eligible_degrees,
            "eligible_fields": record.eligible_fields,
            "graduation_year_requirements": record.graduation_year_requirements,
            "age_requirements": record.age_requirements,
        }.items()
        if value
    }
    employment = record.employment_type or ("INTERNSHIP" if record.content_type == "INTERNSHIP" else None)
    return {
        "title": record.title,
        "location": record.location,
        "city": record.city,
        "state_or_region": record.state_or_region,
        "country": record.country,
        "employment_type": _enum(EmploymentType, employment, EmploymentType.UNSPECIFIED),
        "work_mode": _enum(WorkMode, record.work_mode, WorkMode.UNSPECIFIED),
        "experience_level": _enum(ExperienceLevel, record.experience_level, None),
        "industry": record.industry,
        "salary_min": record.salary_min,
        "salary_max": record.salary_max,
        "salary_currency": record.salary_currency,
        "salary_period": record.salary_period,
        "short_summary": record.summary,
        "description": record.description,
        "responsibilities": _nonempty(record.responsibilities),
        "requirements": _nonempty(record.requirements),
        "preferred_skills": _nonempty(record.preferred_skills),
        "education_requirements": _nonempty(record.education_requirements),
        "experience_requirements": _nonempty(record.experience_requirements),
        "application_url": record.application_url,
        "source_url": record.source_url,
        "source_published_at": record.published_at,
        "application_deadline": record.application_deadline,
        "expires_at": record.expires_at,
        "opportunity_type": _enum(OpportunityType, record.content_type, OpportunityType.JOB),
        "external_job_id": record.source_external_id,
        "requisition_id": record.requisition_id,
        "program_duration": record.program_duration,
        "program_start_date": record.program_start_date,
        "eligibility_json": eligibility or None,
    }


def scholarship_fields(record: ExtractedScholarship) -> dict:
    return {
        "name": record.name,
        "organization": record.provider,
        "country": record.country,
        "degree_levels": _nonempty(record.degree_levels),
        "fields_of_study": _nonempty(record.fields_of_study),
        "funding_type": _enum(FundingType, record.funding_type, FundingType.UNSPECIFIED),
        "tuition_coverage": record.tuition_coverage,
        "monthly_stipend": record.stipend,
        "travel_support": record.travel_support,
        "insurance_support": record.insurance_support,
        "accommodation_support": record.accommodation_support,
        "summary": record.summary,
        "description": record.description,
        "eligible_nationalities": _nonempty(record.eligible_nationalities),
        "academic_requirements": _nonempty(record.academic_requirements),
        "experience_requirements": _nonempty(record.experience_requirements),
        "language_requirements": _nonempty(record.language_requirements),
        "age_requirement": record.age_requirements,
        "required_documents": _nonempty(record.required_documents),
        "official_url": record.official_application_url,
        "source_url": record.source_url,
        "application_deadline": record.deadline,
        "opening_date": record.opening_date,
        "award_type": AwardType.FELLOWSHIP if record.content_type == "FELLOWSHIP" else AwardType.SCHOLARSHIP,
    }


def intelligence_fields(record: ExtractedIntelligence) -> dict:
    return {
        "headline": record.headline,
        "category": _enum(IntelligenceCategory, record.category, IntelligenceCategory.OTHER),
        "summary": record.summary,
        # Never the full article (copyright): only the factual summary and the source link.
        "full_content": None,
        "why_it_matters": record.career_relevance,
        "relevant_roles": _nonempty(record.relevant_roles),
        "relevant_skills": _nonempty(record.relevant_skills),
        "source_url": record.source_url,
        "source_published_at": record.published_at,
        "source_name": record.source_name,
    }


def provenance_fields(source: ContentSource, *, verified: bool) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "source_type": SourceType(source.source_type.value if hasattr(source.source_type, "value") else source.source_type),
        "content_source_id": source.id,
        "last_verified_at": now,
        "is_verified": verified,
        "is_demo": False,
    }


def build_job(record: ExtractedJob, *, source: ContentSource, company_id: str, slug: str, status: ContentStatus, admin_id: str | None, verified: bool) -> Job:
    return Job(
        company_id=company_id, slug=slug, status=status, created_by_admin_id=admin_id,
        source_state=SourceState.ACTIVE, **job_fields(record), **provenance_fields(source, verified=verified),
    )


def build_scholarship(record: ExtractedScholarship, *, source: ContentSource, slug: str, status: ContentStatus, admin_id: str | None, verified: bool) -> Scholarship:
    return Scholarship(
        slug=slug, status=status, created_by_admin_id=admin_id, source_state=SourceState.ACTIVE,
        **scholarship_fields(record), **provenance_fields(source, verified=verified),
    )


def build_intelligence(record: ExtractedIntelligence, *, source: ContentSource, company_id: str | None, slug: str, status: ContentStatus, admin_id: str | None, verified: bool) -> IntelligencePost:
    fields = provenance_fields(source, verified=verified)
    return IntelligencePost(company_id=company_id, slug=slug, status=status, created_by_admin_id=admin_id, **intelligence_fields(record), **fields)


# ------------------------------------------------------------------------------------------------
# Change detection
# ------------------------------------------------------------------------------------------------

# Mutable facts compared against the stored record (spec §20). Editorial fields (featured flags,
# images, why_it_matters written by an editor) are never overwritten from a source.
TRACKED_FIELDS = {
    ENTITY_JOB: ("title", "application_deadline", "description", "requirements", "location", "application_url"),
    ENTITY_SCHOLARSHIP: ("name", "application_deadline", "description", "academic_requirements", "official_url", "country"),
    ENTITY_INTELLIGENCE: ("headline", "summary", "source_url"),
}


def _comparable(value):
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return aware.date().isoformat()  # deadline changes are day-level facts
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return [" ".join(str(v).split()) for v in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _serializable(value):
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return aware.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, str) and len(value) > 4000:
        return value[:4000] + "…"
    return value


def fields_for(entity_type: str, record: ExtractedRecord) -> dict:
    if entity_type == ENTITY_JOB:
        return job_fields(record)  # type: ignore[arg-type]
    if entity_type == ENTITY_SCHOLARSHIP:
        return scholarship_fields(record)  # type: ignore[arg-type]
    return intelligence_fields(record)  # type: ignore[arg-type]


def diff_record(entity_type: str, entity, record: ExtractedRecord) -> list[tuple[str, object, object]]:
    """[(field, old, new)] for tracked fields where the source now states something different.
    A field the source no longer states (None/empty) is not treated as a removal of the fact."""
    proposed = fields_for(entity_type, record)
    changes = []
    for field in TRACKED_FIELDS[entity_type]:
        new = proposed.get(field)
        if new in (None, [], ""):
            continue
        old = getattr(entity, field, None)
        if _comparable(old) != _comparable(new):
            changes.append((field, _serializable(old), _serializable(new)))
    return changes


def coerce_for_field(entity_type: str, field: str, value):
    """Turn a stored JSON change value back into the column's Python type when applying it."""
    from app.ingestion.text import parse_datetime

    if field in ("application_deadline", "expires_at", "opening_date", "source_published_at", "program_start_date"):
        return parse_datetime(value)
    return value


def canonical(url: str | None) -> str | None:
    return canonicalize_url(url) if url else None


def normalized(text: str | None) -> str:
    return normalize_title(text or "")
