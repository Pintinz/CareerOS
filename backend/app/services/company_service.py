from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.repositories.intelligence_repository import CompanyFollowRepository
from app.schemas.company import CompanyCreate, CompanyOut, CompanyUpdate


class CompanyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CompanyRepository(db)
        self.follows = CompanyFollowRepository(db)

    async def list_public(self, *, page: int, page_size: int, search: str | None, viewer_user_id: str | None = None):
        items, total = await self.repo.list_paginated(
            page=page, page_size=page_size, search=search, active_only=True
        )
        followed_ids = await self.follows.list_followed_company_ids(viewer_user_id) if viewer_user_id else set()
        out = [self._to_out(c, is_following=c.id in followed_ids) for c in items]
        return out, total

    async def list_admin(self, *, page: int, page_size: int, search: str | None):
        return await self.repo.list_paginated(
            page=page, page_size=page_size, search=search, active_only=False
        )

    @staticmethod
    def _to_out(company: Company, *, is_following: bool = False) -> CompanyOut:
        out = CompanyOut.model_validate(company)
        out.is_following = is_following
        return out

    async def get_public(self, id_or_slug: str, *, viewer_user_id: str | None = None) -> CompanyOut:
        company = await self.repo.get_by_id_or_slug(id_or_slug)
        if company is None or not company.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        is_following = False
        if viewer_user_id:
            is_following = await self.follows.get(viewer_user_id, company.id) is not None
        return self._to_out(company, is_following=is_following)

    async def follow(self, user_id: str, company_id: str) -> None:
        company = await self.repo.get_by_id(company_id)
        if company is None or not company.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        await self.follows.follow(user_id, company_id)
        await self.db.commit()

    async def unfollow(self, user_id: str, company_id: str) -> None:
        await self.follows.unfollow(user_id, company_id)
        await self.db.commit()

    async def list_followed(self, user_id: str) -> list[CompanyOut]:
        followed_ids = await self.follows.list_followed_company_ids(user_id)
        companies = [await self.repo.get_by_id(cid) for cid in followed_ids]
        return [self._to_out(c, is_following=True) for c in companies if c is not None]

    async def get_for_admin(self, company_id: str) -> Company:
        company = await self.repo.get_by_id(company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return company

    async def create(self, payload: CompanyCreate) -> Company:
        slug = await self.repo.generate_unique_slug(payload.name)
        company = Company(slug=slug, **payload.model_dump())
        await self.repo.create(company)
        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def update(self, company_id: str, payload: CompanyUpdate) -> Company:
        company = await self.get_for_admin(company_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def delete(self, company_id: str) -> None:
        company = await self.get_for_admin(company_id)
        await self.repo.delete(company)
        await self.db.commit()
