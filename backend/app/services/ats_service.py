from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching import ats_engine
from app.models.ats_analysis import AtsAnalysis
from app.models.cv_document import CvDocument
from app.repositories.ats_repository import AtsRepository
from app.repositories.cv_repository import CvRepository
from app.repositories.job_repository import JobRepository
from app.schemas.ats import AtsAnalyzeRequest
from app.services.document_extraction import extract_text

MAX_CV_BYTES = 5 * 1024 * 1024  # 5MB — a text-based CV has no business being larger


class AtsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cvs = CvRepository(db)
        self.jobs = JobRepository(db)
        self.analyses = AtsRepository(db)

    async def upload_cv(self, user_id: str, file: UploadFile, *, name: str | None, is_primary: bool) -> CvDocument:
        content = await file.read()
        if len(content) > MAX_CV_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"CV file exceeds the {MAX_CV_BYTES // (1024 * 1024)}MB limit",
            )

        text = extract_text(filename=file.filename, content=content, content_type=file.content_type)

        cv = CvDocument(
            user_id=user_id,
            name=name or file.filename or "My CV",
            original_filename=file.filename,
            extracted_text=text,
            is_primary=is_primary,
        )
        await self.cvs.create(cv)
        await self.db.commit()
        await self.db.refresh(cv)
        return cv

    async def list_cvs(self, user_id: str) -> list[CvDocument]:
        return await self.cvs.list_for_user(user_id)

    async def delete_cv(self, user_id: str, cv_id: str) -> None:
        cv = await self.cvs.get_owned(cv_id, user_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
        await self.cvs.delete(cv)
        await self.db.commit()

    async def analyze(self, user_id: str, payload: AtsAnalyzeRequest) -> AtsAnalysis:
        cv_text, cv_document_id = await self._resolve_cv_text(user_id, payload)
        job_description, job_id, job_title = await self._resolve_job_description(payload)

        result = ats_engine.analyze(cv_text=cv_text, job_description=job_description, job_title=job_title)

        analysis = AtsAnalysis(
            user_id=user_id,
            cv_document_id=cv_document_id,
            job_id=job_id,
            job_description_text=None if job_id else job_description,
            job_title=job_title,
            overall_score=result.overall_score,
            score_breakdown=result.score_breakdown(ats_engine.DEFAULT_ATS_WEIGHTS),
            strong_matches=result.strong_matches,
            missing_keywords=result.missing_keywords,
            formatting_issues=result.formatting_issues,
            missing_metrics_note=result.missing_metrics_note,
        )
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    async def _resolve_cv_text(self, user_id: str, payload: AtsAnalyzeRequest) -> tuple[str, str | None]:
        if payload.cv_document_id and payload.cv_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide either cv_document_id or cv_text, not both",
            )
        if payload.cv_document_id:
            cv = await self.cvs.get_owned(payload.cv_document_id, user_id)
            if cv is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
            return cv.extracted_text, cv.id
        if payload.cv_text:
            return payload.cv_text, None
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either cv_document_id or cv_text",
        )

    async def _resolve_job_description(
        self, payload: AtsAnalyzeRequest
    ) -> tuple[str, str | None, str | None]:
        if payload.job_id and payload.job_description:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide either job_id or job_description, not both",
            )
        if payload.job_id:
            job = await self.jobs.get_by_id(payload.job_id)
            if job is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            description_parts = [job.short_summary or "", job.description or ""]
            description_parts.extend(job.requirements or [])
            description_parts.extend(job.preferred_skills or [])
            return "\n".join(p for p in description_parts if p), job.id, job.title
        if payload.job_description:
            return payload.job_description, None, payload.job_title
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either job_id or job_description",
        )

    async def list_analyses(self, user_id: str, *, page: int, page_size: int):
        return await self.analyses.list_for_user(user_id, page=page, page_size=page_size)
