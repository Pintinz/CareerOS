from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_ops import AdminNotification, NotificationStatus
from app.repositories.admin_ops_repository import AdminNotificationRepository, AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin_ops import AdminNotificationCreate, UserAdminOut

# The source registry and discovery queue services live with the discovery engine; re-exported
# here so existing imports keep working.
from app.services.discovery.review import ContentSourceService, DiscoveryService  # noqa: F401,E402


class AuditLogService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AuditLogRepository(db)

    async def list_admin(self, **kwargs):
        return await self.repo.list_admin(**kwargs)


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
