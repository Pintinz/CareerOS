from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.intelligence_post import IntelligenceCategory
from app.models.user import User
from app.schemas.intelligence import IntelligenceDetailOut, IntelligenceListResponse
from app.security.dependencies import get_optional_current_user
from app.services.intelligence_service import IntelligenceService

router = APIRouter()


@router.get("", response_model=IntelligenceListResponse)
async def list_intelligence(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    category: IntelligenceCategory | None = None,
    company_id: str | None = None,
    followed_only: bool = False,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_current_user),
) -> IntelligenceListResponse:
    if followed_only and viewer is None:
        return IntelligenceListResponse(items=[], page=page, page_size=page_size, total=0)

    items, total = await IntelligenceService(db).list_public(
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        company_id=company_id,
        followed_by_user_id=viewer.id if (followed_only and viewer) else None,
    )
    return IntelligenceListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{id_or_slug}", response_model=IntelligenceDetailOut)
async def get_intelligence_post(id_or_slug: str, db: AsyncSession = Depends(get_db)) -> IntelligenceDetailOut:
    return await IntelligenceService(db).get_public(id_or_slug)
