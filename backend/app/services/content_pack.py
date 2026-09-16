"""Moving published content (companies, opportunities, news, source registry, media) from one
CareerOS database to another — in practice, from the local development database to the first
production deployment.

Only content tables travel. No user, profile, application, CV, recording, email-tracking or admin
row is ever exported: production starts with real opportunities and zero personal data.

Rows keep their original primary keys, so foreign keys (a job's company, a job's content source)
survive the move and re-importing the same pack updates rows instead of duplicating them.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Table, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import JSON

from app.db.base import Base
# Importing the model modules registers their tables on Base.metadata, which the importer looks up.
from app.models import (  # noqa: F401
    admin_ops,
    company,
    intelligence_post,
    interview,
    job,
    media,
    question,
    scholarship,
)

# Parents before children: a job needs its company and content source to exist first, an option
# needs its question. The practice question banks travel too — without them the Prepare features
# have nothing to serve.
PACK_TABLES = (
    "media_assets",
    "companies",
    "content_sources",
    "jobs",
    "scholarships",
    "intelligence_posts",
    "question_categories",
    "question_topics",
    "questions",
    "question_options",
    "interview_question_categories",
    "interview_topics",
    "interview_questions",
)

# Admin authorship is local to the database it was written in — the target has different admin ids.
_DROP_COLUMNS = {"created_by_admin_id", "reviewed_by_admin_id", "published_by_admin_id"}

# Upload paths are one level deep at most (`/uploads/x.png`, `/uploads/abstract/y.png`).
_UPLOAD_FILE = re.compile(r"/uploads/((?:[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+\.[A-Za-z0-9]+)")

PACK_FILENAME = "content_pack.json"
MEDIA_DIRNAME = "media"


def _referenced_files(rows: list[dict[str, Any]]) -> set[str]:
    """Upload filenames mentioned by any string value in these rows (logos, banners, images)."""
    found: set[str] = set()
    for row in rows:
        for value in row.values():
            if isinstance(value, str) and "/uploads/" in value:
                found.update(_UPLOAD_FILE.findall(value))
    return found


def export_pack(*, sqlite_path: Path, upload_dir: Path, base_url: str, out_dir: Path) -> dict[str, int]:
    """Reads the local SQLite database directly (no app models needed) and writes a portable pack."""
    out_dir.mkdir(parents=True, exist_ok=True)
    media_out = out_dir / MEDIA_DIRNAME
    media_out.mkdir(exist_ok=True)

    connection = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    counts: dict[str, int] = {}
    tables: dict[str, list[dict[str, Any]]] = {}
    files: set[str] = set()
    try:
        for name in PACK_TABLES:
            rows = [
                {key: value for key, value in dict(row).items() if key not in _DROP_COLUMNS}
                for row in connection.execute(f"SELECT * FROM {name}")  # noqa: S608 — fixed table names
            ]
            tables[name] = rows
            counts[name] = len(rows)
            files |= _referenced_files(rows)
    finally:
        connection.close()

    copied = 0
    for filename in sorted(files):
        source = upload_dir / filename
        if source.is_file():
            target = media_out / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
    counts["media_files"] = copied

    pack = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url.rstrip("/"),
        "counts": counts,
        "tables": tables,
    }
    (out_dir / PACK_FILENAME).write_text(json.dumps(pack, indent=1, ensure_ascii=False), encoding="utf-8")
    return counts


def _coerce(table: Table, row: dict[str, Any], *, old_base: str, new_base: str) -> dict[str, Any]:
    """SQLite hands back strings and ints for everything; Postgres needs real datetimes, dates,
    booleans and JSON. Absolute media URLs are rebased onto the target deployment."""
    coerced: dict[str, Any] = {}
    for key, value in row.items():
        column = table.c.get(key)
        if column is None:
            continue  # a column this deployment's schema no longer has
        if isinstance(value, str) and old_base and old_base in value:
            value = value.replace(old_base, new_base)
        if value is None:
            coerced[key] = None
            continue
        kind = column.type
        if isinstance(kind, DateTime) and isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if kind.timezone and parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            coerced[key] = parsed
        elif isinstance(kind, Date) and not isinstance(kind, DateTime) and isinstance(value, str):
            coerced[key] = date.fromisoformat(value[:10])
        elif isinstance(kind, Boolean) and isinstance(value, int):
            coerced[key] = bool(value)
        elif isinstance(kind, JSON) and isinstance(value, str):
            coerced[key] = json.loads(value)
        else:
            coerced[key] = value
    return coerced


async def import_pack(
    session: AsyncSession,
    *,
    pack_dir: Path,
    public_base_url: str,
    upload_dir: Path,
) -> dict[str, int]:
    """Upserts every row in the pack by primary key and restores its media files. Idempotent:
    running it again updates existing rows rather than creating duplicates."""
    pack_file = pack_dir / PACK_FILENAME
    if not pack_file.is_file():
        raise FileNotFoundError(f"No content pack at {pack_file}")
    pack = json.loads(pack_file.read_text(encoding="utf-8"))
    old_base = str(pack.get("base_url", "")).rstrip("/")
    new_base = public_base_url.rstrip("/")

    result: dict[str, int] = {}
    for name in PACK_TABLES:
        rows = pack["tables"].get(name) or []
        table = Base.metadata.tables[name]
        created = updated = 0
        for raw in rows:
            values = _coerce(table, raw, old_base=old_base, new_base=new_base)
            row_id = values.get("id")
            if row_id is None:
                continue
            exists = (await session.execute(select(table.c.id).where(table.c.id == row_id))).first()
            if exists:
                payload = {k: v for k, v in values.items() if k != "id"}
                await session.execute(table.update().where(table.c.id == row_id).values(**payload))
                updated += 1
            else:
                await session.execute(table.insert().values(**values))
                created += 1
        await session.flush()
        result[f"{name}_created"] = created
        result[f"{name}_updated"] = updated
    await session.commit()

    media_dir = pack_dir / MEDIA_DIRNAME
    restored = 0
    if media_dir.is_dir():
        upload_dir.mkdir(parents=True, exist_ok=True)
        for source in media_dir.rglob("*"):
            if source.is_file():
                target = upload_dir / source.relative_to(media_dir)
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    restored += 1
    result["media_files_restored"] = restored
    return result
