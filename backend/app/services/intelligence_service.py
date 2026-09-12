from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence_post import ContentStatus, IntelligencePost
from app.repositories.company_repository import CompanyRepository
from app.repositories.intelligence_repository import IntelligenceRepository
from app.schemas.intelligence import (
    IntelligenceAdminOut,
    IntelligenceCardOut,
    IntelligenceCreate,
    IntelligenceDetailOut,
    IntelligenceUpdate,
)
from app.schemas.job import JobCompanySummary


class IntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IntelligenceRepository(db)
        self.companies = CompanyRepository(db)

    async def _company_summary(self, company_id: str | None) -> JobCompanySummary | None:
        if not company_id:
            return None
        company = await self.companies.get_by_id(company_id)
        return JobCompanySummary.model_validate(company) if company else None

    @staticmethod
    def _fields(post: IntelligencePost, exclude: set[str]) -> dict:
        return {name: getattr(post, name) for name in post.__table__.columns.keys() if name not in exclude}

    async def to_card(self, post: IntelligencePost) -> IntelligenceCardOut:
        data = self._fields(post, exclude={"company_id", "created_by_admin_id"})
        data["company"] = await self._company_summary(post.company_id)
        return IntelligenceCardOut.model_validate(data)

    async def to_detail(self, post: IntelligencePost) -> IntelligenceDetailOut:
        data = self._fields(post, exclude={"company_id", "created_by_admin_id"})
        data["company"] = await self._company_summary(post.company_id)
        return IntelligenceDetailOut.model_validate(data)

    async def to_admin(self, post: IntelligencePost) -> IntelligenceAdminOut:
        data = self._fields(post, exclude=set())
        data["company"] = await self._company_summary(post.company_id)
        return IntelligenceAdminOut.model_validate(data)

    async def list_public(self, **filters):
        items, total = await self.repo.list_public(**filters)
        return [await self.to_card(post) for post in items], total

    async def list_admin(self, *, page: int, page_size: int, search: str | None, post_status: str | None):
        items, total = await self.repo.list_admin(page=page, page_size=page_size, search=search, status=post_status)
        return [await self.to_admin(post) for post in items], total

    async def get_public(self, id_or_slug: str) -> IntelligenceDetailOut:
        post = await self.repo.get_by_id_or_slug(id_or_slug)
        if post is None or post.status != ContentStatus.PUBLISHED or not post.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return await self.to_detail(post)

    async def get_for_admin(self, post_id: str) -> IntelligencePost:
        post = await self.repo.get_by_id(post_id)
        if post is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return post

    async def create(self, payload: IntelligenceCreate) -> IntelligenceAdminOut:
        if payload.company_id and await self.companies.get_by_id(payload.company_id) is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown company_id")

        slug = await self.repo.generate_unique_slug(payload.headline)
        post = IntelligencePost(slug=slug, **payload.model_dump())
        if post.status == ContentStatus.PUBLISHED and post.published_at is None:
            post.published_at = datetime.now(timezone.utc)
        await self.repo.create(post)
        await self.db.commit()
        await self.db.refresh(post)
        return await self.to_admin(post)

    async def update(self, post_id: str, payload: IntelligenceUpdate) -> IntelligenceAdminOut:
        post = await self.get_for_admin(post_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(post, field, value)
        if post.status == ContentStatus.PUBLISHED and post.published_at is None:
            post.published_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(post)
        return await self.to_admin(post)

    async def delete(self, post_id: str) -> None:
        post = await self.get_for_admin(post_id)
        await self.repo.delete(post)
        await self.db.commit()
