import logging

from app.core.request_context import RequestIdLogFilter


def configure_logging() -> None:
    """Minimal, dependency-free structured-enough logging setup (Phase 9.5 audit item 37:
    "production-ready hooks... do not require a paid monitoring service yet"). Every log line
    carries a level, logger name, and the current request id (via RequestIdLogFilter, set by the
    middleware in app/main.py) so an operator can grep one request's full trail out of the logs
    without a dedicated APM tool. Swapping this for a real log shipper (e.g. to Datadog/ELK) later
    only means changing the handler, not any call site."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdLogFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
