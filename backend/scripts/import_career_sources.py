"""Imports a career-source pack (default: the starter company pack) into the source registry.

Idempotent: companies are matched by name and sources by URL; re-running only refreshes each
source's audit metadata and never overrides an admin's operational choices (active, polling, trust,
auto-publish, auto-draft). See CAREER_SOURCE_INTEGRATION.md and docs/career_sources.md.

Usage:
    cd backend && python -m scripts.import_career_sources            # apply
    cd backend && python -m scripts.import_career_sources --dry-run  # show what would change
    cd backend && python -m scripts.import_career_sources --file path/to/pack.json
"""

import argparse
import asyncio

from app.db.session import AsyncSessionLocal
from app.models import (  # noqa: F401 — register every mapper referenced by relationships
    admin_ops, admin_user, application, ats_analysis, company, company_follow, cv_document, email_tracking, intelligence_post,
    interview, job, media, monetization, profile, push, question, scholarship, test_session, user,
)
from app.services.discovery.source_seed import DEFAULT_SEED_PATH, import_career_sources, load_seed


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(DEFAULT_SEED_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pack = load_seed(args.file)
    async with AsyncSessionLocal() as db:
        result = await import_career_sources(db, pack, admin_id=None, dry_run=args.dry_run)
    print(
        f"{'Dry run — ' if result.dry_run else ''}{len(pack.sources)} sources in pack (checked {pack.checked_at}): "
        f"{result.companies_created} companies created, {result.sources_created} sources created, "
        f"{result.sources_updated} updated, {result.sources_unchanged} unchanged"
    )


if __name__ == "__main__":
    asyncio.run(main())
