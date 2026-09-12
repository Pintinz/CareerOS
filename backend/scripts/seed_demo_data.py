"""Seeds fictional demo content for local development (spec §75).

Every record created here is flagged `is_demo=True` so the app can visually badge it and so it
can be bulk-deleted later — this is fictional development data, never real vacancies/scholarships
presented to a production user. Safe to re-run: skips seeding if any demo company already exists.

Usage:
    cd backend && python -m scripts.seed_demo_data
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import AsyncSessionLocal

# Import every model module so SQLAlchemy's mapper registry can resolve cross-model foreign
# keys (e.g. jobs.created_by_admin_id -> admin_users.id) even though this script never touches
# admin_users/users/profiles directly.
from app.models import admin_user, profile, user  # noqa: F401
from app.models.company import Company
from app.models.job import ContentStatus, EmploymentType, ExperienceLevel, Job, SourceType, WorkMode
from app.models.scholarship import DegreeLevel, FundingType, Scholarship
from app.core.slugify import slugify

DEMO_COMPANIES = [
    dict(
        name="Demo Energy Corp",
        industry="Energy",
        country="Nigeria",
        headquarters="Lagos, Nigeria",
        description="Fictional energy company used for local development and demos only.",
        is_verified=True,
    ),
    dict(
        name="Demo FinTech Labs",
        industry="Financial Technology",
        country="Kenya",
        headquarters="Nairobi, Kenya",
        description="Fictional fintech company used for local development and demos only.",
        is_verified=False,
    ),
]

DEMO_JOBS = [
    dict(
        company_name="Demo Energy Corp",
        title="Process Technician",
        location="Lagos, Nigeria",
        country="Nigeria",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        experience_level=ExperienceLevel.MID,
        industry="Energy",
        short_summary="Operate and maintain plant equipment at a fictional demo refinery.",
        application_url="https://example.com/demo-careers/process-technician",
        is_featured=True,
    ),
    dict(
        company_name="Demo FinTech Labs",
        title="Backend Engineer",
        location="Remote",
        country="Kenya",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.REMOTE,
        experience_level=ExperienceLevel.SENIOR,
        industry="Financial Technology",
        short_summary="Build fictional payments infrastructure for demo purposes.",
        application_url="https://example.com/demo-careers/backend-engineer",
        is_urgent=True,
    ),
]

DEMO_SCHOLARSHIPS = [
    dict(
        name="Demo Global Masters Award",
        organization="Demo Foundation",
        country="United Kingdom",
        degree_levels=[DegreeLevel.MASTERS],
        funding_type=FundingType.FULLY_FUNDED,
        summary="Fictional fully-funded masters scholarship used for local development only.",
        official_url="https://example.com/demo-scholarships/global-masters",
        is_featured=True,
    ),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(Company).where(Company.is_demo.is_(True)))).scalars().first()
        if existing is not None:
            print("Demo data already present (found a demo company) — skipping seed.")
            return

        now = datetime.now(timezone.utc)
        companies_by_name: dict[str, Company] = {}

        for data in DEMO_COMPANIES:
            company = Company(slug=slugify(data["name"]), is_demo=True, **data)
            db.add(company)
            await db.flush()
            companies_by_name[data["name"]] = company
            print(f"Created demo company: {company.name}")

        for data in DEMO_JOBS:
            company_name = data.pop("company_name")
            company = companies_by_name[company_name]
            job = Job(
                slug=slugify(f"{data['title']}-{company.name}"),
                company_id=company.id,
                source_type=SourceType.OTHER,
                status=ContentStatus.PUBLISHED,
                published_at=now,
                application_deadline=now + timedelta(days=30),
                is_demo=True,
                **data,
            )
            db.add(job)
            print(f"Created demo job: {job.title} @ {company.name}")

        for data in DEMO_SCHOLARSHIPS:
            scholarship = Scholarship(
                slug=slugify(data["name"]),
                source_type=SourceType.OTHER,
                status=ContentStatus.PUBLISHED,
                published_at=now,
                application_deadline=now + timedelta(days=60),
                is_demo=True,
                **data,
            )
            db.add(scholarship)
            print(f"Created demo scholarship: {scholarship.name}")

        await db.commit()
        print("Demo data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
