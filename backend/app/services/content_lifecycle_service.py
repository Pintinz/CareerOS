"""Scheduled publishing + content expiration (spec §14-15/§37/§41). Both functions are safe to call
twice in a row (or concurrently) — each only ever transitions a row whose status doesn't already
reflect the target state, so a duplicate scheduler tick is a no-op, not a duplicate side effect.

Datetime comparisons are done in Python (not in the SQL `WHERE` clause) because SQLite — used in
dev/test — stores `DateTime(timezone=True)` values as naive strings, and comparing a timezone-aware
bind parameter against them at the SQL level is unreliable; the rest of this codebase (see
`JobService._is_publicly_visible`) already established this same pattern.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence_post import IntelligencePost
from app.models.job import ContentStatus, Job, SourceState
from app.services import audit_service
from app.models.scholarship import Scholarship


def _as_aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def publish_scheduled_content(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    published = 0
    for model in (Job, Scholarship, IntelligencePost):
        result = await db.execute(select(model).where(model.scheduled_publish_at.isnot(None)))
        for row in result.scalars().all():
            if row.status == ContentStatus.PUBLISHED:
                continue
            if _as_aware_utc(row.scheduled_publish_at) > now:
                continue
            row.status = ContentStatus.PUBLISHED
            if row.published_at is None:
                row.published_at = now
            published += 1
    if published:
        await db.commit()
    return published


async def expire_content(db: AsyncSession) -> int:
    """Jobs expire at `expires_at` or, when earlier/only one set, at their `application_deadline`;
    scholarships at `application_deadline`. The row is kept (saved items, applications and CV
    analyses still reference it) and its `source_state` records why. Intelligence posts have no
    expiry concept (news doesn't "expire" the way a time-bound listing does)."""
    now = datetime.now(timezone.utc)
    expired = 0

    result = await db.execute(select(Job).where((Job.expires_at.isnot(None)) | (Job.application_deadline.isnot(None))))
    for job in result.scalars().all():
        if job.status in (ContentStatus.EXPIRED, ContentStatus.ARCHIVED):
            continue
        if job.application_deadline is not None and _as_aware_utc(job.application_deadline) <= now:
            state = SourceState.DEADLINE_PASSED
        elif job.expires_at is not None and _as_aware_utc(job.expires_at) <= now:
            state = SourceState.EXPIRED
        else:
            continue
        job.status = ContentStatus.EXPIRED
        if job.source_state == SourceState.ACTIVE:
            job.source_state = state
        audit_service.add(db, admin_id=None, action="content_expired", entity_type="job", entity_id=job.id, metadata={"reason": state.value})
        expired += 1

    result = await db.execute(select(Scholarship).where(Scholarship.application_deadline.isnot(None)))
    for scholarship in result.scalars().all():
        if scholarship.status in (ContentStatus.EXPIRED, ContentStatus.ARCHIVED) or _as_aware_utc(scholarship.application_deadline) > now:
            continue
        scholarship.status = ContentStatus.EXPIRED
        if scholarship.source_state == SourceState.ACTIVE:
            scholarship.source_state = SourceState.DEADLINE_PASSED
        audit_service.add(db, admin_id=None, action="content_expired", entity_type="scholarship", entity_id=scholarship.id, metadata={"reason": "DEADLINE_PASSED"})
        expired += 1

    if expired:
        await db.commit()
    return expired
