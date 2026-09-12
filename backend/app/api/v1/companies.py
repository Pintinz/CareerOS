from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.company import CompanyListResponse, CompanyOut
from app.security.dependencies import get_current_user, get_optional_current_user
from app.services.company_service import CompanyService

router = APIRouter()


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_current_user),
) -> CompanyListResponse:
    items, total = await CompanyService(db).list_public(
        page=page, page_size=page_size, search=search, viewer_user_id=viewer.id if viewer else None
    )
    return CompanyListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{id_or_slug}", response_model=CompanyOut)
async def get_company(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_current_user),
) -> CompanyOut:
    return await CompanyService(db).get_public(id_or_slug, viewer_user_id=viewer.id if viewer else None)


@router.post("/{company_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_company(
    company_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await CompanyService(db).follow(user.id, company_id)


@router.delete("/{company_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_company(
    company_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await CompanyService(db).unfollow(user.id, company_id)
