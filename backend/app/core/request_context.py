import contextvars
import logging

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdLogFilter(logging.Filter):
    """Injects the current request's id (set by the middleware in app/main.py) into every log
    record so an operator can grep one request's full trail out of the logs — a lightweight
    substitute for a paid APM/tracing tool (Phase 9.5 audit item 37)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
