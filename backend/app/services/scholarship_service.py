from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ContentStatus
from app.models.scholarship import Scholarship
from app.repositories.scholarship_repository import ScholarshipRepository
from app.services.availability import availability_of, is_official_source, publicly_listable, publicly_viewable
from app.schemas.scholarship import (
    ScholarshipAdminOut,
    ScholarshipCardOut,
    ScholarshipCreate,
    ScholarshipDetailOut,
    ScholarshipUpdate,
)


class ScholarshipService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ScholarshipRepository(db)

    @staticmethod
    def _fields(scholarship: Scholarship) -> dict:
        data = {name: getattr(scholarship, name) for name in scholarship.__table__.columns.keys()}
        data["availability"] = availability_of(scholarship)
        data["is_official_source"] = is_official_source(scholarship)
        return data

    def to_card(self, scholarship: Scholarship, *, is_saved: bool = False) -> ScholarshipCardOut:
        data = self._fields(scholarship)
        data["is_saved"] = is_saved
        return ScholarshipCardOut.model_validate(data)

    def to_detail(self, scholarship: Scholarship, *, is_saved: bool = False) -> ScholarshipDetailOut:
        data = self._fields(scholarship)
        data["is_saved"] = is_saved
        return ScholarshipDetailOut.model_validate(data)

    def to_admin(self, scholarship: Scholarship) -> ScholarshipAdminOut:
        return ScholarshipAdminOut.model_validate(self._fields(scholarship))

    async def list_public(self, *, viewer_user_id: str | None = None, **filters):
        items, total = await self.repo.list_public(**filters)
        saved_ids = await self.repo.list_saved_ids(viewer_user_id) if viewer_user_id else set()
        cards = [self.to_card(s, is_saved=s.id in saved_ids) for s in items]
        return cards, total

    async def list_admin(self, *, page: int, page_size: int, search: str | None, scholarship_status: str | None):
        items, total = await self.repo.list_admin(
            page=page, page_size=page_size, search=search, status=scholarship_status
        )
        return [self.to_admin(s) for s in items], total

    async def get_public(self, id_or_slug: str, *, viewer_user_id: str | None = None) -> ScholarshipDetailOut:
        scholarship = await self.repo.get_by_id_or_slug(id_or_slug)
        # Reachable after expiry/removal for saved items; `availability` tells the app not to offer Apply.
        if scholarship is None or not publicly_viewable(scholarship):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found")
        is_saved = False
        if viewer_user_id:
            is_saved = scholarship.id in await self.repo.list_saved_ids(viewer_user_id)
        return self.to_detail(scholarship, is_saved=is_saved)

    async def get_for_admin(self, scholarship_id: str) -> Scholarship:
        scholarship = await self.repo.get_by_id(scholarship_id)
        if scholarship is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found")
        return scholarship

    async def create(self, payload: ScholarshipCreate, *, admin_id: str | None = None) -> ScholarshipAdminOut:
        slug = await self.repo.generate_unique_slug(payload.name)
        scholarship = Scholarship(slug=slug, created_by_admin_id=admin_id, **payload.model_dump())
        self._apply_workflow_transitions(scholarship, admin_id=admin_id)
        await self.repo.create(scholarship)
        await self.db.commit()
        await self.db.refresh(scholarship)
        return self.to_admin(scholarship)

    async def update(self, scholarship_id: str, payload: ScholarshipUpdate, *, admin_id: str | None = None) -> ScholarshipAdminOut:
        scholarship = await self.get_for_admin(scholarship_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(scholarship, field, value)
        self._apply_workflow_transitions(scholarship, admin_id=admin_id)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(scholarship)
        return self.to_admin(scholarship)

    @staticmethod
    def _apply_workflow_transitions(scholarship: Scholarship, *, admin_id: str | None) -> None:
        if scholarship.status == ContentStatus.REVIEW and scholarship.reviewed_by_admin_id is None:
            scholarship.reviewed_by_admin_id = admin_id
        if scholarship.status == ContentStatus.PUBLISHED:
            if scholarship.published_at is None:
                scholarship.published_at = datetime.now(timezone.utc)
            if scholarship.published_by_admin_id is None:
                scholarship.published_by_admin_id = admin_id

    async def delete(self, scholarship_id: str) -> None:
        scholarship = await self.get_for_admin(scholarship_id)
        await self.repo.delete(scholarship)
        await self.db.commit()

    async def save_for_user(self, user_id: str, scholarship_id: str) -> None:
        scholarship = await self.repo.get_by_id(scholarship_id)
        if scholarship is None or not publicly_listable(scholarship):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found")
        await self.repo.save(user_id, scholarship_id)
        await self.db.commit()

    async def unsave_for_user(self, user_id: str, scholarship_id: str) -> None:
        await self.repo.unsave(user_id, scholarship_id)
        await self.db.commit()

    async def list_saved_for_user(self, user_id: str, *, page: int, page_size: int):
        items, total = await self.repo.list_saved(user_id, page=page, page_size=page_size)
        return [self.to_card(s, is_saved=True) for s in items], total
