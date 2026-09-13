from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def list_admin(self, *, page: int, page_size: int, search: str | None) -> tuple[list[User], int]:
        query = select(User)
        count_query = select(func.count()).select_from(User)
        if search:
            like = f"%{search.lower()}%"
            # A user's name lives on Profile, not User — join only when actually searching to
            # keep the common (unfiltered) path a single-table query.
            query = query.outerjoin(Profile, Profile.user_id == User.id).where(
                or_(func.lower(User.email).like(like), func.lower(Profile.full_name).like(like))
            )
            count_query = count_query.outerjoin(Profile, Profile.user_id == User.id).where(
                or_(func.lower(User.email).like(like), func.lower(Profile.full_name).like(like))
            )
        query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, hashed_password: str) -> User:
        user = User(email=email.lower(), hashed_password=hashed_password)
        self.db.add(user)
        await self.db.flush()
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
