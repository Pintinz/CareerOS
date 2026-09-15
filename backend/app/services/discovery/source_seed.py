"""Career-source seed registry: import the starter company pack (or any later pack) into the source
registry without code changes.

The pack is data (`app/seeds/career_sources.json`), validated here and applied idempotently:
- companies are matched by name and created with only the fields the pack states;
- sources are matched by URL. New sources are created as registered; for existing ones only the
  audit metadata (readiness, ATS, job-search URL, note, adapter scope) is refreshed — operational
  choices an admin made (active, polling, trust, auto-publish, auto-draft) are never overwritten.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_ops import ContentSource, DiscoveryMethod, SourceReadiness
from app.models.company import Company
from app.models.job import SourceType
from app.repositories.company_repository import CompanyRepository
from app.schemas.admin_ops import ContentSourceCreate, _validate_adapter_config, _validate_source_url
from app.services import audit_service
from app.services.discovery.review import ContentSourceService

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "seeds" / "career_sources.json"
JOB_TYPES = ["JOB", "INTERNSHIP", "GRADUATE_PROGRAM", "APPRENTICESHIP", "TRAINEE_PROGRAM"]


class SeedSource(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    industry: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=255)
    website_url: str | None = Field(default=None, max_length=1024)
    career_url: str = Field(min_length=1, max_length=1024)
    job_search_url: str | None = Field(default=None, max_length=1024)
    name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=1024)  # the fetched endpoint; defaults to career_url
    source_type: SourceType = SourceType.OFFICIAL_CAREER_PAGE
    discovery_method: DiscoveryMethod | None = None
    ats_provider: str | None = Field(default=None, max_length=40, pattern=r"^[A-Z0-9_]+$")
    readiness: SourceReadiness
    readiness_note: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=255)
    trust_level: int | None = Field(default=None, ge=1, le=5)
    content_types: list[str] = JOB_TYPES
    adapter_config: dict = {}
    polling_enabled: bool = False
    poll_interval_minutes: int | None = Field(default=None, ge=60, le=10_080)

    _urls = field_validator("website_url", "career_url", "job_search_url", "url")(classmethod(lambda cls, v: _validate_source_url(v) if v else v))
    _config = field_validator("adapter_config")(classmethod(lambda cls, v: _validate_adapter_config(v)))

    @property
    def fetch_url(self) -> str:
        return self.url or self.career_url

    @property
    def automated(self) -> bool:
        return self.readiness in (SourceReadiness.READY_STRUCTURED, SourceReadiness.READY_HTML)


class SeedPack(BaseModel):
    version: int
    checked_at: str
    defaults: dict = {}
    sources: list[SeedSource]


@dataclass
class SeedImportResult:
    dry_run: bool
    companies_created: int = 0
    sources_created: int = 0
    sources_updated: int = 0
    sources_unchanged: int = 0
    skipped: list[str] = field(default_factory=list)


def load_seed(path: Path | str = DEFAULT_SEED_PATH) -> SeedPack:
    return SeedPack.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


async def import_career_sources(db: AsyncSession, pack: SeedPack, *, admin_id: str | None, dry_run: bool = False) -> SeedImportResult:
    result = SeedImportResult(dry_run=dry_run)
    companies = CompanyRepository(db)
    sources = ContentSourceService(db)
    by_url = {source.url: source for source in (await db.execute(select(ContentSource))).scalars()}

    for entry in pack.sources:
        company = await companies.get_by_name(entry.company)
        if company is None:
            result.companies_created += 1
            if not dry_run:
                company = Company(
                    name=entry.company, slug=await companies.generate_unique_slug(entry.company),
                    website_url=entry.website_url, career_url=entry.career_url, industry=entry.industry,
                )
                db.add(company)
                await db.flush()
                audit_service.add(db, admin_id=admin_id, action="create", entity_type="company", entity_id=company.id, metadata={"from": "career_source_seed"})

        config = {**pack.defaults.get("adapter_config", {}), **entry.adapter_config} if entry.automated else entry.adapter_config
        existing = by_url.get(entry.fetch_url)
        if existing is None:
            result.sources_created += 1
            if dry_run:
                continue
            method = entry.discovery_method or (None if entry.automated else DiscoveryMethod.MANUAL)
            source = await sources.create(ContentSourceCreate(
                name=entry.name or f"{entry.company} careers", organization=entry.company, url=entry.fetch_url,
                source_type=entry.source_type, country=entry.country, region=entry.region, industry=entry.industry,
                company_id=company.id if company else None, trust_level=entry.trust_level, discovery_method=method,
                content_types=entry.content_types, adapter_config_json=config,
                # Only sources verified as fetchable are polled; the rest are tracked by editors.
                polling_enabled=entry.polling_enabled and entry.automated, crawl_interval_minutes=entry.poll_interval_minutes,
                job_search_url=entry.job_search_url, ats_provider=entry.ats_provider, readiness=entry.readiness,
                readiness_note=entry.readiness_note,
            ), admin_id=admin_id)
            by_url[source.url] = source
            continue

        refreshed = {
            "readiness": entry.readiness, "readiness_note": entry.readiness_note, "ats_provider": entry.ats_provider,
            "job_search_url": entry.job_search_url, "adapter_config_json": {**(existing.adapter_config_json or {}), **config},
        }
        changed = [k for k, v in refreshed.items() if getattr(existing, k) != v]
        if company is not None and existing.company_id is None:
            refreshed["company_id"] = company.id
            changed.append("company_id")
        if not changed:
            result.sources_unchanged += 1
            continue
        result.sources_updated += 1
        if not dry_run:
            for key in changed:
                setattr(existing, key, refreshed[key])
            if not entry.automated and existing.polling_enabled:
                # Audited as not fetchable (blocked, manual or needs configuration): stop polling it.
                existing.polling_enabled = False
                changed.append("polling_enabled")
            audit_service.add(db, admin_id=admin_id, action="source_edited", entity_type="content_source", entity_id=existing.id, metadata={"fields": changed, "from": "career_source_seed"})

    if dry_run:
        await db.rollback()
    else:
        await db.commit()
    return result
