from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationNote, ApplicationStage, ApplicationStageEvent


class ApplicationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_owned(self, application_id: str, user_id: str) -> Application | None:
        result = await self.db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, *, page: int, page_size: int, stage: ApplicationStage | None = None
    ) -> tuple[list[Application], int]:
        query = select(Application).where(Application.user_id == user_id)
        count_query = select(func.count()).select_from(Application).where(Application.user_id == user_id)

        if stage:
            query = query.where(Application.current_stage == stage)
            count_query = count_query.where(Application.current_stage == stage)

        query = query.order_by(Application.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)

        total = (await self.db.execute(count_query)).scalar_one()
        items = (await self.db.execute(query)).scalars().all()
        return list(items), total

    async def count_active_for_user(self, user_id: str, *, terminal_stages: set[ApplicationStage]) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user_id, Application.current_stage.notin_(terminal_stages))
        )
        return result.scalar_one()

    async def create(self, application: Application) -> Application:
        self.db.add(application)
        await self.db.flush()
        return application

    async def update(self, application: Application, **fields: object) -> Application:
        for key, value in fields.items():
            if value is not None:
                setattr(application, key, value)
        await self.db.flush()
        return application

    async def delete(self, application: Application) -> None:
        await self.db.delete(application)

    async def add_stage_event(self, event: ApplicationStageEvent) -> ApplicationStageEvent:
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_timeline(self, application_id: str) -> list[ApplicationStageEvent]:
        result = await self.db.execute(
            select(ApplicationStageEvent)
            .where(ApplicationStageEvent.application_id == application_id)
            .order_by(ApplicationStageEvent.occurred_at.asc())
        )
        return list(result.scalars().all())

    async def add_note(self, note: ApplicationNote) -> ApplicationNote:
        self.db.add(note)
        await self.db.flush()
        return note

    async def get_notes(self, application_id: str) -> list[ApplicationNote]:
        result = await self.db.execute(
            select(ApplicationNote)
            .where(ApplicationNote.application_id == application_id)
            .order_by(ApplicationNote.created_at.desc())
        )
        return list(result.scalars().all())
