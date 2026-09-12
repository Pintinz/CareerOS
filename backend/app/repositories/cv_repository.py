from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cv_document import CvDocument


class CvRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, cv_id: str) -> CvDocument | None:
        result = await self.db.execute(select(CvDocument).where(CvDocument.id == cv_id))
        return result.scalar_one_or_none()

    async def get_owned(self, cv_id: str, user_id: str) -> CvDocument | None:
        result = await self.db.execute(
            select(CvDocument).where(CvDocument.id == cv_id, CvDocument.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[CvDocument]:
        result = await self.db.execute(
            select(CvDocument).where(CvDocument.user_id == user_id).order_by(CvDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, cv: CvDocument) -> CvDocument:
        if cv.is_primary:
            await self._clear_primary(cv.user_id)
        self.db.add(cv)
        await self.db.flush()
        return cv

    async def set_primary(self, cv: CvDocument) -> None:
        await self._clear_primary(cv.user_id)
        cv.is_primary = True
        await self.db.flush()

    async def _clear_primary(self, user_id: str) -> None:
        await self.db.execute(
            update(CvDocument).where(CvDocument.user_id == user_id).values(is_primary=False)
        )

    async def delete(self, cv: CvDocument) -> None:
        await self.db.delete(cv)
