"""Organization matching and duplicate detection for discovered records (spec §19, §36-37).

Deduplication never relies on title equality alone. In order of strength:

Jobs          same source + external id → requisition id (same company) → canonical application /
              listing URL → same company + same location + near-identical title
Scholarships  canonical official URL → provider + normalized name (+ same deadline day if known)
Intelligence  canonical source URL → company + near-identical headline within 3 days

A match against an existing CareerOS record means "this is an update", never a new listing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.schemas import (
    ExtractedIntelligence,
    ExtractedJob,
    ExtractedRecord,
    ExtractedScholarship,
    record_canonical_url,
    record_organization,
)
from app.ingestion.text import normalize_name, title_similarity
from app.ingestion.url_safety import canonicalize_url, registrable_domain
from app.models.admin_ops import ContentSource, DiscoveredItem, DiscoveredItemStatus
from app.models.company import Company
from app.models.intelligence_post import IntelligencePost
from app.models.job import Job
from app.models.scholarship import Scholarship
from app.services.discovery.records import ENTITY_INTELLIGENCE, ENTITY_JOB, ENTITY_SCHOLARSHIP

TITLE_DUPLICATE_THRESHOLD = 0.8
HEADLINE_DUPLICATE_THRESHOLD = 0.85
OPEN_ITEM_STATUSES = (
    DiscoveredItemStatus.NEW, DiscoveredItemStatus.NEEDS_REVIEW, DiscoveredItemStatus.VERIFIED,
    DiscoveredItemStatus.DRAFT_CREATED, DiscoveredItemStatus.PUBLISHED, DiscoveredItemStatus.DUPLICATE,
)


@dataclass
class CompanyMatch:
    company: Company | None
    method: str | None  # SOURCE_LINK / NAME / DOMAIN
    proposal: dict | None = None  # suggested company to create (admin confirms)


@dataclass
class DedupResult:
    same_item: DiscoveredItem | None = None  # this listing was seen before from the same source
    duplicate_of: DiscoveredItem | None = None  # another source's item for the same listing
    entity_type: str | None = None
    entity: object | None = None  # existing CareerOS record → update flow
    reasons: list[str] = field(default_factory=list)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _canon(url: str | None) -> str | None:
    try:
        return canonicalize_url(url) if url else None
    except ValueError:
        return None


async def match_company(db: AsyncSession, source: ContentSource, record: ExtractedRecord) -> CompanyMatch:
    if source.company_id:
        company = await db.get(Company, source.company_id)
        if company is not None:
            return CompanyMatch(company=company, method="SOURCE_LINK")

    organization = record_organization(record) or source.organization
    wanted = normalize_name(organization)
    if wanted:
        # Normalized comparison in Python: names differ in suffixes/punctuation ("Shell plc" / "Shell").
        first_word = wanted.split()[0]
        result = await db.execute(select(Company).where(Company.name.ilike(f"%{first_word}%")).limit(200))
        for company in result.scalars().all():
            if normalize_name(company.name) == wanted:
                return CompanyMatch(company=company, method="NAME")

    source_domain = registrable_domain(source.url)
    official_source = source.source_type.value not in ("AGGREGATOR", "NEWS_MEDIA", "INDUSTRY_PUBLICATION", "RSS", "OTHER")
    if source_domain and official_source:
        result = await db.execute(
            select(Company).where(or_(Company.website_url.ilike(f"%{source_domain}%"), Company.career_url.ilike(f"%{source_domain}%"))).limit(20)
        )
        for company in result.scalars().all():
            if source_domain in {registrable_domain(company.website_url), registrable_domain(company.career_url)}:
                return CompanyMatch(company=company, method="DOMAIN")

    proposal = None
    if organization:
        is_ats_board = source.source_type.value in ("GREENHOUSE", "LEVER", "ASHBY", "SMARTRECRUITERS", "WORKDAY", "SUCCESSFACTORS", "ORACLE")
        proposal = {
            "name": organization,
            # Only what the source itself establishes; industry/headquarters are left for the admin.
            "website_url": None if is_ats_board or not official_source else f"https://{source_domain}" if source_domain else None,
            "career_url": source.url if official_source else None,
            "industry": source.industry,
            "country": None,
        }
    return CompanyMatch(company=None, method=None, proposal=proposal)


async def find_duplicates(
    db: AsyncSession,
    *,
    source: ContentSource,
    record: ExtractedRecord,
    company: Company | None,
    item_types: tuple[str, ...],
) -> DedupResult:
    result = DedupResult()
    external_id = record.source_external_id
    canonical_url = _canon(record_canonical_url(record))
    listing_url = _canon(record.source_url)

    # 1. Same source, same external id (or same URL when the source has no ids).
    conditions = [DiscoveredItem.source_id == source.id]
    if external_id:
        conditions.append(DiscoveredItem.external_id == external_id)
    elif canonical_url:
        conditions.append(DiscoveredItem.canonical_url == canonical_url)
    else:
        conditions = None
    if conditions:
        existing = (await db.execute(select(DiscoveredItem).where(*conditions).order_by(DiscoveredItem.created_at.asc()).limit(1))).scalar_one_or_none()
        if existing is not None:
            result.same_item = existing
            result.reasons.append("same_source_external_id" if external_id else "same_source_url")

    # 2. Existing CareerOS records.
    if isinstance(record, ExtractedJob):
        await _match_job(db, result, source=source, record=record, company=company, urls={u for u in (canonical_url, listing_url) if u})
    elif isinstance(record, ExtractedScholarship):
        await _match_scholarship(db, result, record=record, urls={u for u in (canonical_url, listing_url) if u})
    elif isinstance(record, ExtractedIntelligence):
        await _match_intelligence(db, result, record=record, company=company, url=listing_url)

    # 3. The same listing already queued from another source.
    if result.same_item is None and result.entity is None and canonical_url:
        other = (
            await db.execute(
                select(DiscoveredItem)
                .where(DiscoveredItem.canonical_url == canonical_url, DiscoveredItem.source_id != source.id, DiscoveredItem.status.in_(OPEN_ITEM_STATUSES), DiscoveredItem.item_type.in_(item_types))
                .order_by(DiscoveredItem.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if other is not None:
            result.duplicate_of = other
            result.reasons.append("same_canonical_url_other_source")
    return result


async def _match_job(db, result: DedupResult, *, source: ContentSource, record: ExtractedJob, company: Company | None, urls: set[str]) -> None:
    candidates: list[Job] = []
    if record.source_external_id:
        candidates += (await db.execute(select(Job).where(Job.content_source_id == source.id, Job.external_job_id == record.source_external_id))).scalars().all()
        if candidates:
            result.entity_type, result.entity = ENTITY_JOB, candidates[0]
            result.reasons.append("record_same_source_external_id")
            return
    if company is None:
        # Without an organization, only exact URL matches are safe.
        url_values = [u for u in (*urls, record.application_url, record.source_url) if u]
        rows = (await db.execute(select(Job).where(or_(Job.application_url.in_(url_values), Job.source_url.in_(url_values))).limit(5))).scalars().all()
        if rows:
            result.entity_type, result.entity = ENTITY_JOB, rows[0]
            result.reasons.append("record_same_url")
        return

    company_jobs = (await db.execute(select(Job).where(Job.company_id == company.id).order_by(Job.created_at.desc()).limit(1000))).scalars().all()
    if record.requisition_id:
        for job in company_jobs:
            if job.requisition_id and job.requisition_id.strip().lower() == record.requisition_id.strip().lower():
                result.entity_type, result.entity = ENTITY_JOB, job
                result.reasons.append("record_same_requisition_id")
                return
    for job in company_jobs:
        if {_canon(job.application_url), _canon(job.source_url)} & urls:
            result.entity_type, result.entity = ENTITY_JOB, job
            result.reasons.append("record_same_url")
            return
    location = normalize_name(record.location or record.city or record.country) or ""
    for job in company_jobs:
        same_location = (normalize_name(job.location or job.city or job.country) or "") == location
        if same_location and title_similarity(job.title, record.title) >= TITLE_DUPLICATE_THRESHOLD:
            result.entity_type, result.entity = ENTITY_JOB, job
            result.reasons.append("record_similar_title_same_company_location")
            return


async def _match_scholarship(db, result: DedupResult, *, record: ExtractedScholarship, urls: set[str]) -> None:
    url_values = [u for u in (*urls, record.official_application_url, record.source_url) if u]
    rows = (await db.execute(select(Scholarship).where(or_(Scholarship.official_url.in_(url_values), Scholarship.source_url.in_(url_values))).limit(5))).scalars().all()
    if rows:
        result.entity_type, result.entity = ENTITY_SCHOLARSHIP, rows[0]
        result.reasons.append("record_same_official_url")
        return
    provider = normalize_name(record.provider)
    if not provider:
        return
    first_word = normalize_name(record.name).split()[0] if normalize_name(record.name) else ""
    candidates = (await db.execute(select(Scholarship).where(Scholarship.name.ilike(f"%{first_word}%")).limit(300))).scalars().all()
    for scholarship in candidates:
        if normalize_name(scholarship.organization) != provider:
            continue
        if title_similarity(scholarship.name, record.name) < TITLE_DUPLICATE_THRESHOLD:
            continue
        stored, found = _aware(scholarship.application_deadline), _aware(record.deadline)
        if stored and found and stored.date() != found.date():
            # Same programme name and provider but a different deadline is most likely next year's
            # cycle — still the same record if the old deadline already passed (a new cycle update).
            if stored > datetime.now(timezone.utc):
                continue
        result.entity_type, result.entity = ENTITY_SCHOLARSHIP, scholarship
        result.reasons.append("record_same_provider_similar_name")
        return


async def _match_intelligence(db, result: DedupResult, *, record: ExtractedIntelligence, company: Company | None, url: str | None) -> None:
    if url:
        rows = (await db.execute(select(IntelligencePost).where(IntelligencePost.source_url.in_([url, record.source_url])).limit(1))).scalars().all()
        if rows:
            result.entity_type, result.entity = ENTITY_INTELLIGENCE, rows[0]
            result.reasons.append("record_same_source_url")
            return
    if company is None:
        return
    posts = (await db.execute(select(IntelligencePost).where(IntelligencePost.company_id == company.id).order_by(IntelligencePost.created_at.desc()).limit(300))).scalars().all()
    published = _aware(record.published_at)
    for post in posts:
        if title_similarity(post.headline, record.headline) < HEADLINE_DUPLICATE_THRESHOLD:
            continue
        stored = _aware(post.source_published_at)
        if published and stored and abs(stored - published) > timedelta(days=3):
            continue
        result.entity_type, result.entity = ENTITY_INTELLIGENCE, post
        result.reasons.append("record_same_company_similar_headline")
        return
