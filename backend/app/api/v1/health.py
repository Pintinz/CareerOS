from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/liveness")
async def liveness() -> dict:
    """Phase 11 (spec §24): process is up and serving requests. Deliberately checks nothing
    external — a liveness probe that depends on the database or a third-party provider causes an
    orchestrator to restart a perfectly healthy process just because Postgres/Gmail/AdMob had a
    blip, which is the wrong failure mode for a liveness check specifically."""
    return {"status": "alive"}


@router.get("/readiness")
async def readiness(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """Phase 11 (spec §24): checks the one dependency that actually makes this instance unable to
    serve real traffic — the database. Deliberately does NOT check Gmail/Outlook/AdMob/storage:
    those are optional integrations (see PROJECT_STATUS.md's release philosophy) whose outage
    must never take a healthy backend instance out of a load balancer's rotation."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "unreachable"}
