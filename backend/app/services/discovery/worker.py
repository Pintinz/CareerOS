"""Asynchronous discovery execution (spec §29-30).

- The admin "Run Discovery" action only *enqueues* a DiscoveryRun row and returns immediately.
- A background task (in-process) and the scheduler's dispatcher both drain the queue; a run is
  claimed with a conditional UPDATE (QUEUED → RUNNING), so two workers never execute the same run.
- The dispatcher also enqueues sources whose crawl interval elapsed (respecting backoff after 429s
  and failures) and fails runs whose worker died mid-flight.

There is no second scheduler: the dispatcher is a job in `app/scheduler.py`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.error_reporting import report_exception
from app.models.admin_ops import (
    ContentSource,
    DiscoveryRun,
    DiscoveryRunStatus,
    DiscoveryRunTrigger,
    DiscoveryRunType,
)
from app.services.discovery.pipeline import DiscoveryPipeline

logger = logging.getLogger("careeros.discovery.worker")

STALE_RUN_AFTER = timedelta(hours=1)
_OPEN = (DiscoveryRunStatus.QUEUED, DiscoveryRunStatus.RUNNING)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def enqueue_source_run(
    db: AsyncSession, source: ContentSource, *, trigger: DiscoveryRunTrigger, admin_id: str | None = None
) -> tuple[DiscoveryRun, bool]:
    """Returns (run, created). An already queued/running run for the source is reused, so repeated
    clicks or overlapping dispatcher ticks never pile up work against one website."""
    existing = (
        await db.execute(
            select(DiscoveryRun)
            .where(DiscoveryRun.source_id == source.id, DiscoveryRun.status.in_(_OPEN), DiscoveryRun.run_type == DiscoveryRunType.SOURCE_DISCOVERY)
            .order_by(DiscoveryRun.queued_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False
    run = DiscoveryRun(
        source_id=source.id, run_type=DiscoveryRunType.SOURCE_DISCOVERY, trigger=trigger, status=DiscoveryRunStatus.QUEUED,
        requested_by_admin_id=admin_id, queued_at=_now(), stats_json={},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run, True


async def claim_run(db: AsyncSession, run_id: str) -> DiscoveryRun | None:
    result = await db.execute(
        update(DiscoveryRun)
        .where(DiscoveryRun.id == run_id, DiscoveryRun.status == DiscoveryRunStatus.QUEUED)
        .values(status=DiscoveryRunStatus.RUNNING, started_at=_now())
    )
    await db.commit()
    if result.rowcount != 1:
        return None
    return await db.get(DiscoveryRun, run_id, populate_existing=True)


async def process_run(db: AsyncSession, run_id: str, *, pipeline_factory: Callable[[AsyncSession], DiscoveryPipeline] | None = None) -> DiscoveryRun | None:
    run = await claim_run(db, run_id)
    if run is None:
        return None
    pipeline = (pipeline_factory or DiscoveryPipeline)(db)
    try:
        return await pipeline.execute(run)
    except Exception as exc:  # noqa: BLE001 — record the failure on the run; never crash the worker
        await db.rollback()
        report_exception(exc, source="discovery", run_id=run_id)
        run = await db.get(DiscoveryRun, run_id, populate_existing=True)
        if run is not None and run.status == DiscoveryRunStatus.RUNNING:
            run.status = DiscoveryRunStatus.FAILED
            run.finished_at = _now()
            run.error_code = "INTERNAL_ERROR"
            run.error_message = type(exc).__name__
            await db.commit()
        return run


async def enqueue_due_sources(db: AsyncSession, *, settings: Settings | None = None, now: datetime | None = None) -> int:
    settings = settings or get_settings()
    if not settings.web_discovery_enabled:
        return 0
    now = now or _now()
    sources = (await db.execute(select(ContentSource).where(ContentSource.is_active.is_(True), ContentSource.polling_enabled.is_(True)))).scalars().all()
    queued = 0
    for source in sources:
        if source.discovery_method.value == "MANUAL":
            continue
        if source.next_poll_after and _aware(source.next_poll_after) > now:
            continue
        last = _aware(source.last_checked_at)
        if last and last + timedelta(minutes=max(source.crawl_interval_minutes, 30)) > now:
            continue
        _, created = await enqueue_source_run(db, source, trigger=DiscoveryRunTrigger.SCHEDULED)
        queued += int(created)
    return queued


async def fail_stale_runs(db: AsyncSession, *, now: datetime | None = None) -> int:
    now = now or _now()
    stale = (await db.execute(select(DiscoveryRun).where(DiscoveryRun.status == DiscoveryRunStatus.RUNNING))).scalars().all()
    count = 0
    for run in stale:
        if _aware(run.started_at) and _aware(run.started_at) + STALE_RUN_AFTER < now:
            run.status = DiscoveryRunStatus.FAILED
            run.finished_at = now
            run.error_code = "WORKER_LOST"
            run.error_message = "The worker stopped before the run finished"
            count += 1
    if count:
        await db.commit()
    return count


async def dispatch(db: AsyncSession, session_factory, *, settings: Settings | None = None) -> dict:
    """Scheduler job body: fail stale runs, enqueue due sources, then execute a few queued runs,
    each in its own session."""
    settings = settings or get_settings()
    stale = await fail_stale_runs(db)
    queued = await enqueue_due_sources(db, settings=settings)
    run_ids = (
        await db.execute(
            select(DiscoveryRun.id).where(DiscoveryRun.status == DiscoveryRunStatus.QUEUED).order_by(DiscoveryRun.queued_at.asc()).limit(settings.discovery_runs_per_dispatch)
        )
    ).scalars().all()
    executed = 0
    for run_id in run_ids:
        async with session_factory() as run_db:
            if await process_run(run_db, run_id) is not None:
                executed += 1
    return {"stale_failed": stale, "queued": queued, "executed": executed}


class DiscoveryTaskRunner:
    """Starts queued runs right away in the background so the admin request returns immediately.
    If the process restarts before the task runs, the dispatcher picks the QUEUED run up later."""

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory
        self._tasks: set[asyncio.Task] = set()

    def _factory(self):
        if self._session_factory is None:
            from app.db.session import AsyncSessionLocal

            self._session_factory = AsyncSessionLocal
        return self._session_factory

    async def _run(self, run_id: str) -> None:
        try:
            async with self._factory()() as db:
                await process_run(db, run_id)
        except Exception as exc:  # noqa: BLE001
            report_exception(exc, source="discovery.task", run_id=run_id)

    def enqueue(self, run_id: str) -> None:
        self._spawn(self._run(run_id))

    async def _verify(self, trigger: DiscoveryRunTrigger) -> None:
        from app.services.discovery.verification import verify_active_opportunities

        try:
            async with self._factory()() as db:
                await verify_active_opportunities(db, trigger=trigger)
        except Exception as exc:  # noqa: BLE001
            report_exception(exc, source="discovery.verification")

    def enqueue_verification(self, trigger: DiscoveryRunTrigger = DiscoveryRunTrigger.MANUAL) -> None:
        self._spawn(self._verify(trigger))

    def _spawn(self, coro) -> None:
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


_task_runner = DiscoveryTaskRunner()


def get_discovery_task_runner() -> DiscoveryTaskRunner:
    """FastAPI dependency; tests override it with a runner that records run ids."""
    return _task_runner
