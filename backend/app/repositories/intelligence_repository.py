from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slugify import slugify
from app.models.company_follow import CompanyFollow
from app.models.intelligence_post import ContentStatus, IntelligencePost


class IntelligenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, post_id: str) -> IntelligencePost | None:
        result = await self.db.execute(select(IntelligencePost).where(IntelligencePost.id == post_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> IntelligencePost | None:
        result = await self.db.execute(select(IntelligencePost).where(IntelligencePost.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id_or_slug(self, id_or_slug: str) -> IntelligencePost | None:
        return await self.get_by_id(id_or_slug) or await self.get_by_slug(id_or_slug)

    async def generate_unique_slug(self, headline: str) -> str:
        base_slug = slugify(headline)
        slug = base_slug
        suffix = 1
        while await self.get_by_slug(slug) is not None:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    async def list_public(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        category: str | None = None,
        company_id: str | None = None,
        followed_by_user_id: str | None = None,
    ) -> tuple[list[IntelligencePost], int]:
        query = select(IntelligencePost)
        count_query = select(func.count()).select_from(IntelligencePost)

        conditions = [IntelligencePost.status == ContentStatus.PUBLISHED, IntelligencePost.is_active.is_(True)]
        if search:
            pattern = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(IntelligencePost.headline).like(pattern),
                    func.lower(IntelligencePost.summary).like(pattern),
                )
            )
        if category:
            conditions.append(IntelligencePost.category == category)
        if company_id:
            conditions.append(IntelligencePost.company_id == company_id)

        if followed_by_user_id:
            query = query.join(CompanyFollow, CompanyFollow.company_id == IntelligencePost.company_id)
            count_query = count_query.join(
                CompanyFollow, CompanyFollow.company_id == IntelligencePost.company_id
            )
            conditions.append(CompanyFollow.user_id == followed_by_user_id)

        for condition in conditions:
            query = query.where(condition)
            count_query = count_query.where(condition)

        query = (
            query.order_by(IntelligencePost.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().unique().all()
        return list(items), total

    async def list_admin(
        self, *, page: int, page_size: int, search: str | None = None, status: str | None = None
    ) -> tuple[list[IntelligencePost], int]:
        query = select(IntelligencePost)
        count_query = select(func.count()).select_from(IntelligencePost)
        if status:
            query = query.where(IntelligencePost.status == status)
            count_query = count_query.where(IntelligencePost.status == status)
        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(func.lower(IntelligencePost.headline).like(pattern))
            count_query = count_query.where(func.lower(IntelligencePost.headline).like(pattern))

        query = query.order_by(IntelligencePost.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def create(self, post: IntelligencePost) -> IntelligencePost:
        self.db.add(post)
        await self.db.flush()
        return post

    async def delete(self, post: IntelligencePost) -> None:
        await self.db.delete(post)


class CompanyFollowRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: str, company_id: str) -> CompanyFollow | None:
        result = await self.db.execute(
            select(CompanyFollow).where(CompanyFollow.user_id == user_id, CompanyFollow.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def follow(self, user_id: str, company_id: str) -> CompanyFollow:
        existing = await self.get(user_id, company_id)
        if existing:
            return existing
        follow = CompanyFollow(user_id=user_id, company_id=company_id)
        self.db.add(follow)
        await self.db.flush()
        return follow

    async def unfollow(self, user_id: str, company_id: str) -> None:
        existing = await self.get(user_id, company_id)
        if existing:
            await self.db.delete(existing)

    async def list_followed_company_ids(self, user_id: str) -> set[str]:
        result = await self.db.execute(select(CompanyFollow.company_id).where(CompanyFollow.user_id == user_id))
        return set(result.scalars().all())

    async def follower_count(self, company_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(CompanyFollow).where(CompanyFollow.company_id == company_id)
        )
        return result.scalar_one()
