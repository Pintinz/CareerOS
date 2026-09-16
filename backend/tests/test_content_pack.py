"""Content pack: moving published content (and only published content) between databases."""

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.job import Job
from app.services.content_pack import PACK_FILENAME, import_pack


def _write_pack(tmp_path: Path, *, base_url: str = "http://localhost:8000") -> Path:
    pack_dir = tmp_path / "content_pack"
    (pack_dir / "media").mkdir(parents=True)
    (pack_dir / "media" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    pack = {
        "exported_at": "2026-09-16T00:00:00+00:00",
        "base_url": base_url,
        "counts": {},
        "tables": {
            "media_assets": [
                {
                    "id": "m1",
                    "storage_key": "logo.png",
                    "url": f"{base_url}/uploads/logo.png",
                    "mime_type": "image/png",
                    "width": 128,
                    "height": 128,
                    "file_size": 12,
                    "alt_text": None,
                    "created_at": "2026-09-01 10:00:00",
                    "updated_at": "2026-09-01 10:00:00",
                }
            ],
            "companies": [
                {
                    "id": "c1",
                    "name": "Live Energy Plc",
                    "slug": "live-energy",
                    "logo_url": f"{base_url}/uploads/logo.png",
                    "industry": "Energy",
                    "country": "Nigeria",
                    "is_verified": 1,
                    "is_active": 1,
                    "is_demo": 0,
                    "created_at": "2026-09-01 10:00:00",
                    "updated_at": "2026-09-01 10:00:00",
                }
            ],
            "content_sources": [],
            "jobs": [
                {
                    "id": "j1",
                    "company_id": "c1",
                    "title": "Process Engineer",
                    "slug": "process-engineer",
                    "country": "Nigeria",
                    "employment_type": "FULL_TIME",
                    "work_mode": "ON_SITE",
                    "status": "PUBLISHED",
                    "opportunity_type": "JOB",
                    "source_type": "OFFICIAL_CAREER_PAGE",
                    "source_state": "ACTIVE",
                    "is_verified": 1,
                    "is_featured": 0,
                    "is_urgent": 0,
                    "is_active": 1,
                    "is_demo": 0,
                    "published_at": "2026-09-10 08:30:00",
                    "application_deadline": "2026-10-30 00:00:00",
                    "eligibility_json": '{"eligible_degrees": ["B.Eng"]}',
                    "created_at": "2026-09-10 08:30:00",
                    "updated_at": "2026-09-10 08:30:00",
                }
            ],
            "scholarships": [],
            "intelligence_posts": [],
        },
    }
    (pack_dir / PACK_FILENAME).write_text(json.dumps(pack), encoding="utf-8")
    return pack_dir


@pytest.mark.asyncio
async def test_import_creates_content_rebases_media_and_restores_files(db_session: AsyncSession, tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path)
    uploads = tmp_path / "uploads"

    counts = await import_pack(
        db_session, pack_dir=pack_dir, public_base_url="https://api.careeros.app", upload_dir=uploads
    )

    assert counts["companies_created"] == 1
    assert counts["jobs_created"] == 1
    assert counts["media_files_restored"] == 1
    assert (uploads / "logo.png").is_file()

    company = (await db_session.execute(select(Company).where(Company.id == "c1"))).scalar_one()
    # Absolute media URLs follow the deployment they now live on.
    assert company.logo_url == "https://api.careeros.app/uploads/logo.png"
    assert company.is_verified is True

    job = (await db_session.execute(select(Job).where(Job.id == "j1"))).scalar_one()
    assert job.company_id == "c1"
    assert job.published_at is not None and job.published_at.year == 2026
    assert job.eligibility_json == {"eligible_degrees": ["B.Eng"]}


@pytest.mark.asyncio
async def test_importing_twice_updates_instead_of_duplicating(db_session: AsyncSession, tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path)
    uploads = tmp_path / "uploads"
    await import_pack(db_session, pack_dir=pack_dir, public_base_url="https://api.careeros.app", upload_dir=uploads)

    pack_file = pack_dir / PACK_FILENAME
    pack = json.loads(pack_file.read_text(encoding="utf-8"))
    pack["tables"]["jobs"][0]["title"] = "Senior Process Engineer"
    pack_file.write_text(json.dumps(pack), encoding="utf-8")

    counts = await import_pack(
        db_session, pack_dir=pack_dir, public_base_url="https://api.careeros.app", upload_dir=uploads
    )

    assert counts["jobs_created"] == 0
    assert counts["jobs_updated"] == 1
    assert (await db_session.execute(select(func.count()).select_from(Job.__table__))).scalar_one() == 1
    job = (await db_session.execute(select(Job).where(Job.id == "j1"))).scalar_one()
    assert job.title == "Senior Process Engineer"


@pytest.mark.asyncio
async def test_pack_carries_no_user_or_admin_data(tmp_path: Path) -> None:
    """The exporter's table list and dropped columns are the privacy guarantee — assert them
    directly so nobody quietly adds `users` or an admin foreign key to the pack."""
    from app.services.content_pack import PACK_TABLES, _DROP_COLUMNS

    forbidden = {"users", "profiles", "applications", "cv_documents", "email_connections", "admin_users"}
    assert forbidden.isdisjoint(set(PACK_TABLES))
    assert {"created_by_admin_id", "reviewed_by_admin_id", "published_by_admin_id"} <= _DROP_COLUMNS
