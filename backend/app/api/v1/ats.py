from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.ats import (
    AtsAnalysisListResponse,
    AtsAnalysisOut,
    AtsAnalyzeRequest,
    CvDocumentListResponse,
    CvDocumentOut,
)
from app.security.dependencies import get_current_user
from app.services.ats_service import AtsService
from app.services.monetization_service import MonetizationService

router = APIRouter()


@router.post("/cv", response_model=CvDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    is_primary: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CvDocumentOut:
    cv = await AtsService(db).upload_cv(user.id, file, name=name, is_primary=is_primary)
    return CvDocumentOut.model_validate(cv)


@router.get("/cv", response_model=CvDocumentListResponse)
async def list_cvs(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CvDocumentListResponse:
    cvs = await AtsService(db).list_cvs(user.id)
    items = [CvDocumentOut.model_validate(cv) for cv in cvs]
    return CvDocumentListResponse(items=items, page=1, page_size=len(items) or 1, total=len(items))


@router.delete("/cv/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(
    cv_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await AtsService(db).delete_cv(user.id, cv_id)


@router.post("/analyze", response_model=AtsAnalysisOut)
async def analyze(
    payload: AtsAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AtsAnalysisOut:
    await MonetizationService(db).enforce_ats_limit(user)
    analysis = await AtsService(db).analyze(user.id, payload)
    return AtsAnalysisOut.model_validate(analysis)


@router.get("/analyses", response_model=AtsAnalysisListResponse)
async def list_analyses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AtsAnalysisListResponse:
    items, total = await AtsService(db).list_analyses(user.id, page=page, page_size=page_size)
    return AtsAnalysisListResponse(
        items=[AtsAnalysisOut.model_validate(a) for a in items], page=page, page_size=page_size, total=total
    )
