"""The one background-job scheduler for this codebase (spec §37 — "do not introduce multiple
competing schedulers"). Built on APScheduler's `AsyncIOScheduler`, started/stopped from
`app.main`'s lifespan. Every job opens its own short-lived `AsyncSession` (jobs don't run inside a
request, so there's no request-scoped session to reuse) and is written to be safely callable twice
in a row — see each service function's own idempotency notes.

Jobs registered here (spec §38-39, closing the Phase 8 gap):
  - Gmail/Outlook watch-and-subscription renewal (`EmailTrackingService.renew_expiring_watches`)
  - Scheduled content publishing (`content_lifecycle_service.publish_scheduled_content`)
  - Content expiration (`content_lifecycle_service.expire_content`)

Source-discovery polling (spec §37's fourth bullet) is deliberately NOT registered — no ingestion
adapter exists in this codebase to poll (see ARCHITECTURE.md's Discovery section); registering a
job with nothing behind it would be dead weight, not architecture.
"""

import logging
import zlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from app.core.error_reporting import report_exception
from app.db.session import AsyncSessionLocal, engine
from app.services import content_lifecycle_service
from app.services.email_tracking_service import EmailTrackingService

logger = logging.getLogger("careeros.scheduler")

_scheduler: AsyncIOScheduler | None = None


def _lock_key(job_name: str) -> int:
    return zlib.crc32(job_name.encode("utf-8"))


@asynccontextmanager
async def leader_lock(job_name: str, *, bind=None) -> AsyncIterator[bool]:
    """Phase 11 (spec §22) — scheduler leader election. Every backend process (each gunicorn worker
    in every replica) runs its own in-process `AsyncIOScheduler`, so every timer fires in every
    process at roughly the same moment. Without this, email watch renewal, scheduled publishing,
    and content expiration would run once per process.

    Yields True only in the one process that obtains a Postgres session-level advisory lock for
    this job. The lock lives on a *dedicated* connection held for the whole job and is explicitly
    released in `finally`. It must not be taken through the job's ORM session: the jobs commit
    internally, after which the session may continue on a different pooled connection, and a
    pooled connection is never closed on release — so a session-level lock taken there would
    never be released and its hold count would grow on every tick.

    On SQLite there is no advisory-lock primitive and no multi-process deployment story, so this
    always yields True (a documented single-instance assumption)."""
    bind = bind if bind is not None else engine
    if not bind.dialect.name.startswith("postgresql"):
        yield True
        return

    async with bind.connect() as conn:
        acquired = bool((await conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": _lock_key(job_name)})).scalar_one())
        try:
            yield acquired
        finally:
            if acquired:
                await conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _lock_key(job_name)})

#: Last-run bookkeeping surfaced on the Operations dashboard (spec §42's "Background Jobs: Last
#: Run / Success / Failure / Duration") — process-local, intentionally not persisted: it describes
#: "since this backend process started," which is exactly what an ops dashboard wants to know.
JOB_RUN_HISTORY: dict[str, dict] = {}


async def _run_tracked(job_name: str, coro_factory) -> None:
    started_at = datetime.now(timezone.utc)
    try:
        async with leader_lock(job_name) as is_leader:
            if not is_leader:
                logger.debug("Scheduler job %s skipped — another process holds the leader lock", job_name)
                return
            async with AsyncSessionLocal() as db:
                result = await coro_factory(db)
        JOB_RUN_HISTORY[job_name] = {
            "last_run_at": started_at,
            "duration_seconds": (datetime.now(timezone.utc) - started_at).total_seconds(),
            "success": True,
            "result": result,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — a scheduled job must never crash the scheduler thread.
        report_exception(exc, source="scheduler", job=job_name)
        JOB_RUN_HISTORY[job_name] = {
            "last_run_at": started_at,
            "duration_seconds": (datetime.now(timezone.utc) - started_at).total_seconds(),
            "success": False,
            "result": None,
            "error": str(exc),
        }


async def _renew_email_watches(db) -> int:
    return await EmailTrackingService(db).renew_expiring_watches()


async def _publish_scheduled(db) -> int:
    return await content_lifecycle_service.publish_scheduled_content(db)


async def _expire_content(db) -> int:
    return await content_lifecycle_service.expire_content(db)


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_tracked, "interval", hours=24, id="email_watch_renewal",
        args=["email_watch_renewal", _renew_email_watches], next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(
        _run_tracked, "interval", minutes=15, id="scheduled_content_publish",
        args=["scheduled_content_publish", _publish_scheduled], next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(
        _run_tracked, "interval", hours=1, id="content_expiration",
        args=["content_expiration", _expire_content], next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_job_run_history() -> dict[str, dict]:
    return dict(JOB_RUN_HISTORY)
