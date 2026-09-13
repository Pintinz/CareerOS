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
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services import content_lifecycle_service
from app.services.email_tracking_service import EmailTrackingService

logger = logging.getLogger("careeros.scheduler")

_scheduler: AsyncIOScheduler | None = None

_is_postgres = get_settings().database_url.startswith("postgresql")


async def _acquire_leader_lock(db, job_name: str) -> bool:
    """Phase 11 (spec §22) — scheduler leader election. If multiple backend instances each run
    their own in-process `AsyncIOScheduler` (this codebase's simplest deployment option, spec
    §22: "prefer simplicity... a dedicated scheduler service is acceptable" — but nothing stops
    an operator from running more than one API instance too), every instance's timer fires at
    roughly the same moment, and without this, Gmail/Outlook watch renewal, scheduled publishing,
    and content expiration would each run once **per instance** — redundant at best (wasted
    provider API calls, risking rate limits) and duplicate-side-effect-risking at worst.

    Uses a Postgres session-level advisory lock (`pg_try_advisory_lock`) keyed by a stable hash of
    the job name — the simplest correct primitive for "at most one instance proceeds," with no
    extra infrastructure (no Redis/ZooKeeper) beyond the database every instance already needs.
    The lock is scoped to this one `AsyncSession`'s underlying connection and is automatically
    released the moment that connection closes (this function's caller always closes it
    immediately after the job body runs) — never needs an explicit unlock or a lease-expiry timer.

    On SQLite (this codebase's only actually-exercised database — see DATABASE.md), there is no
    advisory-lock primitive and no realistic multi-instance deployment story, so this always
    returns True (single-instance assumption, documented, not silently pretended away)."""
    if not _is_postgres:
        return True
    lock_key = zlib.crc32(job_name.encode("utf-8"))
    result = await db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key})
    return bool(result.scalar_one())

#: Last-run bookkeeping surfaced on the Operations dashboard (spec §42's "Background Jobs: Last
#: Run / Success / Failure / Duration") — process-local, intentionally not persisted: it describes
#: "since this backend process started," which is exactly what an ops dashboard wants to know.
JOB_RUN_HISTORY: dict[str, dict] = {}


async def _run_tracked(job_name: str, coro_factory) -> None:
    started_at = datetime.now(timezone.utc)
    try:
        async with AsyncSessionLocal() as db:
            if not await _acquire_leader_lock(db, job_name):
                logger.debug("Scheduler job %s skipped — another instance holds the leader lock", job_name)
                return
            result = await coro_factory(db)
        JOB_RUN_HISTORY[job_name] = {
            "last_run_at": started_at,
            "duration_seconds": (datetime.now(timezone.utc) - started_at).total_seconds(),
            "success": True,
            "result": result,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — a scheduled job must never crash the scheduler thread.
        logger.exception("Scheduled job %s failed", job_name)
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
