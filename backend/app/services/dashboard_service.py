"""Live admin dashboard + Operations dashboard data (spec §3/§42-44). Every number here is a real
COUNT query against real tables — no fabricated/placeholder figures anywhere, per explicit spec
instruction."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.admin_ops import ContentSource, DiscoveredItem, DiscoveredItemStatus
from app.models.application import Application
from app.models.company import Company
from app.models.email_tracking import EmailConnection, EmailConnectionStatus, EmailProvider
from app.models.intelligence_post import IntelligencePost
from app.models.job import ContentStatus, Job
from app.models.question import Question
from app.models.interview import InterviewQuestion
from app.models.scholarship import Scholarship
from app.models.user import User
from app.scheduler import get_job_run_history


async def _count(db: AsyncSession, model, *filters) -> int:
    query = select(func.count()).select_from(model)
    for f in filters:
        query = query.where(f)
    return (await db.execute(query)).scalar_one()


async def get_dashboard(db: AsyncSession) -> dict:
    return {
        "users": await _count(db, User),
        "published_jobs": await _count(db, Job, Job.status == ContentStatus.PUBLISHED),
        "published_scholarships": await _count(db, Scholarship, Scholarship.status == ContentStatus.PUBLISHED),
        "companies": await _count(db, Company),
        "intelligence_posts": await _count(db, IntelligencePost, IntelligencePost.status == ContentStatus.PUBLISHED),
        "aptitude_questions": await _count(db, Question),
        "interview_questions": await _count(db, InterviewQuestion),
        "applications_tracked": await _count(db, Application),
        "content_status": {
            "jobs": await _content_status_breakdown(db, Job),
            "scholarships": await _content_status_breakdown(db, Scholarship),
            "intelligence": await _content_status_breakdown(db, IntelligencePost),
        },
        "gmail_connections": await _count(db, EmailConnection, EmailConnection.provider == EmailProvider.GMAIL, EmailConnection.disconnected_at.is_(None)),
        "outlook_connections": await _count(db, EmailConnection, EmailConnection.provider == EmailProvider.OUTLOOK, EmailConnection.disconnected_at.is_(None)),
        "connections_requiring_reauth": await _count(db, EmailConnection, EmailConnection.status == EmailConnectionStatus.REAUTHORIZATION_REQUIRED),
        "failed_email_syncs": await _count(db, EmailConnection, EmailConnection.status == EmailConnectionStatus.ERROR),
        "discovery_items_awaiting_review": await _count(db, DiscoveredItem, DiscoveredItem.status == DiscoveredItemStatus.PENDING),
    }


async def _content_status_breakdown(db: AsyncSession, model) -> dict[str, int]:
    result = await db.execute(select(model.status, func.count()).group_by(model.status))
    return {status.value: count for status, count in result.all()}


async def get_operations(db: AsyncSession) -> dict:
    settings = get_settings()
    return {
        "email_tracking": {
            "active_gmail_connections": await _count(db, EmailConnection, EmailConnection.provider == EmailProvider.GMAIL, EmailConnection.disconnected_at.is_(None)),
            "active_outlook_connections": await _count(db, EmailConnection, EmailConnection.provider == EmailProvider.OUTLOOK, EmailConnection.disconnected_at.is_(None)),
            "reauthorization_required": await _count(db, EmailConnection, EmailConnection.status == EmailConnectionStatus.REAUTHORIZATION_REQUIRED),
            "sync_errors": await _count(db, EmailConnection, EmailConnection.status == EmailConnectionStatus.ERROR),
            "gmail_provider_status": _provider_health("gmail", settings.gmail_tracking_available),
            "outlook_provider_status": _provider_health("outlook", settings.outlook_tracking_available),
        },
        "content_ingestion": {
            "active_sources": await _count(db, ContentSource, ContentSource.is_active.is_(True)),
            "failed_sources": await _count(db, ContentSource, ContentSource.last_error.isnot(None)),
            "discovered_today": await _discovered_today(db),
            "awaiting_review": await _count(db, DiscoveredItem, DiscoveredItem.status == DiscoveredItemStatus.PENDING),
        },
        "background_jobs": get_job_run_history(),
    }


async def _discovered_today(db: AsyncSession) -> int:
    from datetime import datetime, timezone

    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return await _count(db, DiscoveredItem, DiscoveredItem.created_at >= start_of_day)


def _provider_health(name: str, available: bool) -> dict:
    """Never says "Verified" unless a real provider has actually been successfully exercised
    (spec §43) — in this environment that's never true, so this is always Mock/Disabled."""
    if available:
        return {"status": "HEALTHY", "detail": f"{name.title()} credentials configured."}
    return {"status": "DISABLED", "detail": "Mock/Disabled — production credentials not configured."}
