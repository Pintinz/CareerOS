import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_ops import (
    AdminNotification,
    ContentSource,
    DiscoveredItem,
    DiscoveredItemStatus,
    DiscoveredItemType,
    NotificationStatus,
)
from app.models.intelligence_post import IntelligenceCategory, IntelligencePost
from app.models.job import ContentStatus, Job
from app.models.scholarship import Scholarship
from app.repositories.admin_ops_repository import (
    AdminNotificationRepository,
    AuditLogRepository,
    ContentSourceRepository,
    DiscoveredItemRepository,
)
from app.repositories.company_repository import CompanyRepository
from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.job_repository import JobRepository
from app.repositories.scholarship_repository import ScholarshipRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin_ops import (
    AdminNotificationCreate,
    ContentSourceCreate,
    ContentSourceUpdate,
    DiscoveredItemCreate,
    DiscoveryDraftIn,
    UserAdminOut,
)


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


class AuditLogService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AuditLogRepository(db)

    async def list_admin(self, **kwargs):
        return await self.repo.list_admin(**kwargs)


class ContentSourceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ContentSourceRepository(db)

    async def list_all(self) -> list[ContentSource]:
        return await self.repo.list_all()

    async def get_or_404(self, source_id: str) -> ContentSource:
        source = await self.repo.get_by_id(source_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
        return source

    async def create(self, payload: ContentSourceCreate, *, admin_id: str | None) -> ContentSource:
        source = self.repo.add(ContentSource(created_by_admin_id=admin_id, **payload.model_dump()))
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def update(self, source_id: str, payload: ContentSourceUpdate) -> ContentSource:
        source = await self.get_or_404(source_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(source, field, value)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def delete(self, source_id: str) -> None:
        source = await self.get_or_404(source_id)
        await self.repo.delete(source)
        await self.db.commit()


class DiscoveryService:
    """Spec §25-27. Nothing here ever auto-publishes: `create_draft` always creates a
    `ContentStatus.DRAFT` row and marks the discovered item `REVIEWED`, never `PUBLISHED`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DiscoveredItemRepository(db)
        self.sources = ContentSourceRepository(db)
        self.jobs = JobRepository(db)
        self.scholarships = ScholarshipRepository(db)
        self.intelligence = IntelligenceRepository(db)
        self.companies = CompanyRepository(db)

    async def list_admin(self, **kwargs):
        return await self.repo.list_admin(**kwargs)

    async def get_or_404(self, item_id: str) -> DiscoveredItem:
        item = await self.repo.get_by_id(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovered item not found")
        return item

    async def ingest(self, payload: DiscoveredItemCreate) -> DiscoveredItem | None:
        """Returns None (rather than raising) when this is a duplicate of an already-tracked item
        (spec §27) — the caller (a future real adapter, or this phase's manual/test entry point)
        should treat that as a safe no-op, exactly like the Phase 8 webhook dedup pattern."""
        source = await self.sources.get_by_id(payload.source_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown source_id")
        normalized = _normalize_title(payload.detected_title)
        duplicate = await self.repo.find_duplicate(
            source_id=payload.source_id, external_id=payload.external_id, normalized_title=normalized, original_url=payload.original_url
        )
        if duplicate:
            return None
        item = self.repo.add(
            DiscoveredItem(
                source_id=payload.source_id,
                item_type=payload.item_type,
                external_id=payload.external_id,
                detected_title=payload.detected_title,
                detected_company_name=payload.detected_company_name,
                original_url=payload.original_url,
                raw_payload_json=payload.raw_payload,
                normalized_title=normalized,
            )
        )
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def ignore(self, item_id: str, *, admin_id: str | None) -> DiscoveredItem:
        item = await self.get_or_404(item_id)
        item.status = DiscoveredItemStatus.IGNORED
        item.reviewed_by_admin_id = admin_id
        item.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return item

    async def reject(self, item_id: str, *, admin_id: str | None) -> DiscoveredItem:
        item = await self.get_or_404(item_id)
        item.status = DiscoveredItemStatus.REJECTED
        item.reviewed_by_admin_id = admin_id
        item.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return item

    async def create_draft(self, item_id: str, payload: DiscoveryDraftIn, *, admin_id: str | None) -> dict:
        item = await self.get_or_404(item_id)
        if item.status != DiscoveredItemStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item has already been reviewed.")

        draft_id: str
        if item.item_type == DiscoveredItemType.JOB:
            if not payload.company_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="company_id is required for a job draft")
            company = await self.companies.get_by_id(payload.company_id)
            if company is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown company_id")
            slug = await self.jobs.generate_unique_slug(payload.title, company.name)
            from app.models.job import EmploymentType, WorkMode

            job = Job(
                slug=slug,
                company_id=payload.company_id,
                title=payload.title,
                short_summary=payload.summary,
                description=payload.description,
                employment_type=EmploymentType.FULL_TIME,
                work_mode=WorkMode.ON_SITE,
                source_url=item.original_url,
                status=ContentStatus.DRAFT,
                created_by_admin_id=admin_id,
            )
            await self.jobs.create(job)
            await self.db.flush()
            draft_id = job.id
        elif item.item_type == DiscoveredItemType.SCHOLARSHIP:
            slug = await self.scholarships.generate_unique_slug(payload.title)
            scholarship = Scholarship(
                slug=slug,
                name=payload.title,
                organization=payload.company_id,
                summary=payload.summary,
                description=payload.description,
                source_url=item.original_url,
                status=ContentStatus.DRAFT,
                created_by_admin_id=admin_id,
            )
            await self.scholarships.create(scholarship)
            await self.db.flush()
            draft_id = scholarship.id
        else:
            slug = await self.intelligence.generate_unique_slug(payload.title)
            category = IntelligenceCategory(payload.category) if payload.category else IntelligenceCategory.OTHER
            post = IntelligencePost(
                slug=slug,
                company_id=payload.company_id,
                headline=payload.title,
                category=category,
                summary=payload.summary,
                full_content=payload.description,
                source_url=item.original_url,
                status=ContentStatus.DRAFT,
                created_by_admin_id=admin_id,
            )
            await self.intelligence.create(post)
            await self.db.flush()
            draft_id = post.id

        item.status = DiscoveredItemStatus.REVIEWED
        item.created_draft_id = draft_id
        item.reviewed_by_admin_id = admin_id
        item.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {"item_type": item.item_type.value, "draft_id": draft_id}


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AdminNotificationRepository(db)

    async def list_admin(self, **kwargs):
        return await self.repo.list_admin(**kwargs)

    async def get_or_404(self, notification_id: str) -> AdminNotification:
        notification = await self.repo.get_by_id(notification_id)
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return notification

    async def create(self, payload: AdminNotificationCreate, *, admin_id: str | None) -> AdminNotification:
        status_value = NotificationStatus.SCHEDULED if payload.scheduled_at else NotificationStatus.DRAFT
        notification = self.repo.add(
            AdminNotification(**payload.model_dump(), status=status_value, created_by_admin_id=admin_id)
        )
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def send_now(self, notification_id: str) -> AdminNotification:
        """No FCM/APNs credentials are configured in this environment (see PROJECT_STATUS.md) —
        this marks the campaign SENT and records who *would* have received it, without touching
        any user's device or private data. A real delivery integration replaces the body of this
        method only; the API contract (status transitions to SENT, records recipient_count)
        doesn't need to change."""
        notification = await self.get_or_404(notification_id)
        if notification.status == NotificationStatus.SENT:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already sent.")
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
        notification.recipient_count = 0  # honestly zero — no delivery channel exists to count.
        await self.db.commit()
        return notification


class UserAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)

    async def list_admin(self, *, page: int, page_size: int, search: str | None) -> tuple[list[UserAdminOut], int]:
        from sqlalchemy import func, select

        from app.models.application import Application
        from app.models.profile import Profile

        users, total = await self.repo.list_admin(page=page, page_size=page_size, search=search)
        out = []
        for user in users:
            profile_result = await self.db.execute(select(Profile.full_name).where(Profile.user_id == user.id))
            full_name = profile_result.scalar_one_or_none()
            count_result = await self.db.execute(
                select(func.count()).select_from(Application).where(Application.user_id == user.id)
            )
            out.append(
                UserAdminOut(
                    id=user.id, email=user.email, full_name=full_name, is_active=user.is_active,
                    is_verified=user.is_verified, applications_tracked=count_result.scalar_one(), created_at=user.created_at,
                )
            )
        return out, total

    async def set_active(self, user_id: str, *, is_active: bool) -> None:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.is_active = is_active
        await self.db.commit()
