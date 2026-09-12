from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ats_analysis import AtsAnalysis


class AtsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, analysis: AtsAnalysis) -> AtsAnalysis:
        self.db.add(analysis)
        await self.db.flush()
        return analysis

    async def get_owned(self, analysis_id: str, user_id: str) -> AtsAnalysis | None:
        result = await self.db.execute(
            select(AtsAnalysis).where(AtsAnalysis.id == analysis_id, AtsAnalysis.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, *, page: int, page_size: int
    ) -> tuple[list[AtsAnalysis], int]:
        query = (
            select(AtsAnalysis)
            .where(AtsAnalysis.user_id == user_id)
            .order_by(AtsAnalysis.created_at.desc())
        )
        count_query = select(func.count()).select_from(AtsAnalysis).where(AtsAnalysis.user_id == user_id)

        total = (await self.db.execute(count_query)).scalar_one()
        items = (
            (await self.db.execute(query.offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )
        return list(items), total
