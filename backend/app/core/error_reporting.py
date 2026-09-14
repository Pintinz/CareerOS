"""Provider-agnostic error reporting hook (Phase 11, spec §27).

No error-monitoring service is configured in this environment. Every unexpected failure — API 500s,
database errors, scheduled job failures — goes through `report_exception`, so attaching a real
provider later means calling `set_error_reporter` once at startup, with no route or job changes.

Context passed here must stay safe: request method/path, job name, request id. Never request
bodies, headers, tokens, CV text, email content, or any other user data (spec §26/§27).
"""

import logging
from collections.abc import Callable

from app.core.request_context import request_id_var

logger = logging.getLogger("careeros.errors")

ErrorReporter = Callable[[BaseException, dict[str, str]], None]


def _log_reporter(exc: BaseException, context: dict[str, str]) -> None:
    logger.error("unexpected_error %s", context, exc_info=(type(exc), exc, exc.__traceback__))


_reporter: ErrorReporter = _log_reporter


def set_error_reporter(reporter: ErrorReporter | None) -> None:
    global _reporter
    _reporter = reporter or _log_reporter


def report_exception(exc: BaseException, *, source: str, **context: str) -> None:
    payload = {"source": source, "request_id": request_id_var.get(), **context}
    try:
        _reporter(exc, payload)
    except Exception:  # noqa: BLE001 — a broken reporter must never break the request or job.
        logger.exception("error reporter failed")
