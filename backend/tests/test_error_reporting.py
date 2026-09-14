import pytest

from app import scheduler
from app.core.error_reporting import report_exception, set_error_reporter

pytestmark = pytest.mark.asyncio


async def test_failed_scheduled_job_is_reported_with_safe_context_only() -> None:
    captured = []
    set_error_reporter(lambda exc, context: captured.append((exc, context)))
    try:
        async def failing_job(db):
            raise RuntimeError("provider exploded")

        await scheduler._run_tracked("unit_test_job", failing_job)
    finally:
        set_error_reporter(None)

    assert len(captured) == 1
    exc, context = captured[0]
    assert isinstance(exc, RuntimeError)
    assert context["source"] == "scheduler"
    assert context["job"] == "unit_test_job"
    assert set(context) == {"source", "job", "request_id"}
    assert scheduler.JOB_RUN_HISTORY["unit_test_job"]["success"] is False


async def test_a_broken_reporter_never_propagates() -> None:
    def broken(exc, context):
        raise ValueError("reporter is down")

    set_error_reporter(broken)
    try:
        report_exception(RuntimeError("original"), source="api", path="/x")  # must not raise
    finally:
        set_error_reporter(None)
