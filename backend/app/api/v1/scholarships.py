from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.scholarship import FundingType
from app.models.user import User
from app.schemas.scholarship import ScholarshipDetailOut, ScholarshipListResponse
from app.security.dependencies import get_current_user, get_optional_current_user
from app.services.scholarship_service import ScholarshipService

router = APIRouter()


@router.get("", response_model=ScholarshipListResponse)
async def list_scholarships(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    country: str | None = None,
    degree_level: str | None = None,
    funding_type: FundingType | None = None,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_current_user),
) -> ScholarshipListResponse:
    items, total = await ScholarshipService(db).list_public(
        viewer_user_id=viewer.id if viewer else None,
        page=page,
        page_size=page_size,
        search=search,
        country=country,
        degree_level=degree_level,
        funding_type=funding_type,
    )
    return ScholarshipListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{id_or_slug}", response_model=ScholarshipDetailOut)
async def get_scholarship(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_current_user),
) -> ScholarshipDetailOut:
    return await ScholarshipService(db).get_public(id_or_slug, viewer_user_id=viewer.id if viewer else None)


@router.post("/{scholarship_id}/save", status_code=status.HTTP_204_NO_CONTENT)
async def save_scholarship(
    scholarship_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await ScholarshipService(db).save_for_user(user.id, scholarship_id)


@router.delete("/{scholarship_id}/save", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_scholarship(
    scholarship_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await ScholarshipService(db).unsave_for_user(user.id, scholarship_id)
