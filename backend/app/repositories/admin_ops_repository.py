from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_ops import (
    AdminNotification,
    AuditLog,
    ContentSource,
    DiscoveredItem,
    DiscoveredItemStatus,
    DiscoveredItemType,
)


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_admin(
        self, *, page: int, page_size: int, entity_type: str | None = None, admin_id: str | None = None
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
            count_query = count_query.where(AuditLog.entity_type == entity_type)
        if admin_id:
            query = query.where(AuditLog.admin_id == admin_id)
            count_query = count_query.where(AuditLog.admin_id == admin_id)
        query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total


class ContentSourceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self) -> list[ContentSource]:
        result = await self.db.execute(select(ContentSource).order_by(ContentSource.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, source_id: str) -> ContentSource | None:
        result = await self.db.execute(select(ContentSource).where(ContentSource.id == source_id))
        return result.scalar_one_or_none()

    async def count_active(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(ContentSource).where(ContentSource.is_active.is_(True)))
        return result.scalar_one()

    def add(self, source: ContentSource) -> ContentSource:
        self.db.add(source)
        return source

    async def delete(self, source: ContentSource) -> None:
        await self.db.delete(source)


class DiscoveredItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_admin(
        self, *, item_type: DiscoveredItemType | None, item_status: DiscoveredItemStatus | None, page: int, page_size: int
    ) -> tuple[list[DiscoveredItem], int]:
        query = select(DiscoveredItem)
        count_query = select(func.count()).select_from(DiscoveredItem)
        if item_type:
            query = query.where(DiscoveredItem.item_type == item_type)
            count_query = count_query.where(DiscoveredItem.item_type == item_type)
        if item_status:
            query = query.where(DiscoveredItem.status == item_status)
            count_query = count_query.where(DiscoveredItem.status == item_status)
        query = query.order_by(DiscoveredItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def get_by_id(self, item_id: str) -> DiscoveredItem | None:
        result = await self.db.execute(select(DiscoveredItem).where(DiscoveredItem.id == item_id))
        return result.scalar_one_or_none()

    async def count_pending(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(DiscoveredItem).where(DiscoveredItem.status.in_((DiscoveredItemStatus.NEW, DiscoveredItemStatus.NEEDS_REVIEW, DiscoveredItemStatus.VERIFIED)))
        )
        return result.scalar_one()

    def add(self, item: DiscoveredItem) -> DiscoveredItem:
        self.db.add(item)
        return item


class AdminNotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_admin(self, *, page: int, page_size: int) -> tuple[list[AdminNotification], int]:
        query = select(AdminNotification).order_by(AdminNotification.created_at.desc())
        count_query = select(func.count()).select_from(AdminNotification)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return list(items), total

    async def get_by_id(self, notification_id: str) -> AdminNotification | None:
        result = await self.db.execute(select(AdminNotification).where(AdminNotification.id == notification_id))
        return result.scalar_one_or_none()

    def add(self, notification: AdminNotification) -> AdminNotification:
        self.db.add(notification)
        return notification
