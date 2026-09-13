import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.core.request_context import request_id_var
from app.db.session import AsyncSessionLocal
from app.scheduler import start_scheduler, stop_scheduler
from app.services.admin_auth_service import ensure_seed_admin

settings = get_settings()
configure_logging()
logger = logging.getLogger("careeros.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_production and settings.uses_insecure_defaults:
        raise RuntimeError(
            "Refusing to start in production with publicly-committed dev-only secret(s): "
            f"{', '.join(settings.uses_insecure_defaults)}. Set real values via environment/secret "
            "management before deploying — see DEPLOYMENT.md."
        )
    async with AsyncSessionLocal() as session:
        await ensure_seed_admin(
            session, email=settings.admin_seed_email, password=settings.admin_seed_password
        )
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    # Phase 11 (spec §82): interactive API docs/schema are a dev convenience, not something a
    # public production deployment needs to expose — they reveal the full route/schema surface to
    # anyone. Consumer/admin apps never call these; they're purely for human exploration.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    # Phase 11 (spec §83): never "*" — allow_credentials=True with a wildcard origin is both
    # rejected by browsers and a real CSRF-adjacent risk if it weren't. cors_origins_list is a
    # strict, explicit allowlist (see .env.example) — a production deployment must list its real
    # mobile/admin origins here, never widen this to match "anything".
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Phase 11 (spec §82) — headers safe for a JSON API that never renders third-party HTML and
    has no OAuth *redirect* endpoints that receive a browser-set cookie (auth is bearer-token
    only, see SYSTEM_AUDIT.md §18's CSRF finding). No CSP is set: this API returns JSON, not HTML,
    so a content-security-policy would only matter for the dev-only /docs Swagger UI, and setting
    one narrow enough for Swagger's own inline scripts while not breaking it is not worth the
    risk of accidentally breaking OAuth callback pages that redirect through this API — skipped
    rather than shipped half-right."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if settings.is_production:
        # Only meaningful over HTTPS, which is the only way this header could ever be honored —
        # never set in development, where the backend is normally served over plain HTTP.
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Stamps every request with a correlation id (Phase 9.5 audit item 37) — logged on every
    line for that request via RequestIdLogFilter, and echoed back as a response header so a client
    bug report or admin-side error toast can be matched to a specific server-side log trail
    without needing a paid APM tool."""
    request_id = str(uuid.uuid4())
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak a raw exception/stack trace to a client (spec's error-state requirement) while
    still logging the full exception server-side, tagged with the request id, so an operator can
    actually diagnose it — a hook a real error-tracking service (Sentry etc.) can attach to later
    without changing any route."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


app.include_router(api_router, prefix="/api/v1")

_upload_dir = Path(settings.upload_dir)
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")


@app.get("/")
async def root() -> dict:
    return {"service": settings.app_name, "docs": None if settings.is_production else "/docs"}
