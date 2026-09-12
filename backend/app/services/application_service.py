from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import (
    TERMINAL_STAGES,
    Application,
    ApplicationNote,
    ApplicationStage,
    ApplicationStageEvent,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailOut,
    ApplicationNoteCreate,
    ApplicationOut,
    ApplicationStageUpdate,
    ApplicationUpdate,
)


class ApplicationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ApplicationRepository(db)
        self.jobs = JobRepository(db)

    async def create(self, user_id: str, payload: ApplicationCreate) -> ApplicationOut:
        company_name = payload.company_name
        role_title = payload.role_title
        job_url = payload.job_url
        location = payload.location

        if payload.job_id:
            job = await self.jobs.get_by_id(payload.job_id)
            if job is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            company = await CompanyRepository(self.db).get_by_id(job.company_id)
            company_name = company.name if company else "Unknown Company"
            role_title = role_title or job.title
            job_url = job_url or job.application_url
            location = location or job.location
        elif not company_name or not role_title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide job_id, or both company_name and role_title for a manual entry",
            )

        application = Application(
            user_id=user_id,
            job_id=payload.job_id,
            company_name=company_name,
            role_title=role_title,
            location=location,
            job_url=job_url,
            cv_document_id=payload.cv_document_id,
            current_stage=payload.current_stage,
            applied_date=payload.applied_date,
            deadline=payload.deadline,
            salary=payload.salary,
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            cover_letter_text=payload.cover_letter_text,
        )
        await self.repo.create(application)
        await self.repo.add_stage_event(
            ApplicationStageEvent(
                application_id=application.id,
                stage=application.current_stage,
                occurred_at=datetime.now(timezone.utc),
                source="MANUAL",
            )
        )
        await self.db.commit()
        await self.db.refresh(application)
        return ApplicationOut.model_validate(application)

    async def get_for_user(self, user_id: str, application_id: str) -> ApplicationDetailOut:
        application = await self.repo.get_owned(application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        timeline = await self.repo.get_timeline(application_id)
        notes = await self.repo.get_notes(application_id)
        data = ApplicationOut.model_validate(application).model_dump()
        data["timeline"] = timeline
        data["notes"] = notes
        return ApplicationDetailOut.model_validate(data)

    async def list_for_user(self, user_id: str, *, page: int, page_size: int, stage: ApplicationStage | None):
        items, total = await self.repo.list_for_user(user_id, page=page, page_size=page_size, stage=stage)
        return [ApplicationOut.model_validate(a) for a in items], total

    async def count_active_for_user(self, user_id: str) -> int:
        return await self.repo.count_active_for_user(user_id, terminal_stages=TERMINAL_STAGES)

    async def update(self, user_id: str, application_id: str, payload: ApplicationUpdate) -> ApplicationOut:
        application = await self.repo.get_owned(application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        await self.repo.update(application, **payload.model_dump(exclude_unset=True))
        await self.db.commit()
        await self.db.refresh(application)
        return ApplicationOut.model_validate(application)

    async def update_stage(
        self, user_id: str, application_id: str, payload: ApplicationStageUpdate
    ) -> ApplicationDetailOut:
        application = await self.repo.get_owned(application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        application.current_stage = payload.stage
        await self.repo.add_stage_event(
            ApplicationStageEvent(
                application_id=application.id,
                stage=payload.stage,
                occurred_at=payload.occurred_at or datetime.now(timezone.utc),
                note=payload.note,
                source="MANUAL",
            )
        )
        await self.db.commit()
        return await self.get_for_user(user_id, application_id)

    async def delete(self, user_id: str, application_id: str) -> None:
        application = await self.repo.get_owned(application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        await self.repo.delete(application)
        await self.db.commit()

    async def add_note(self, user_id: str, application_id: str, payload: ApplicationNoteCreate):
        application = await self.repo.get_owned(application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        note = await self.repo.add_note(ApplicationNote(application_id=application_id, text=payload.text))
        await self.db.commit()
        await self.db.refresh(note)
        return note
