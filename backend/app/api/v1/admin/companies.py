from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole
from app.schemas.company import CompanyCreate, CompanyListResponse, CompanyOut, CompanyUpdate
from app.security.admin_dependencies import require_admin_role
from app.services.company_service import CompanyService

router = APIRouter()

_CAN_WRITE = require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR)
_CAN_READ = require_admin_role(
    AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.EDITOR, AdminRole.REVIEWER
)


@router.get("", response_model=CompanyListResponse, dependencies=[Depends(_CAN_READ)])
async def list_companies_admin(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> CompanyListResponse:
    items, total = await CompanyService(db).list_admin(page=page, page_size=page_size, search=search)
    return CompanyListResponse(
        items=[CompanyOut.model_validate(c) for c in items], page=page, page_size=page_size, total=total
    )


@router.get("/{company_id}", response_model=CompanyOut, dependencies=[Depends(_CAN_READ)])
async def get_company_admin(company_id: str, db: AsyncSession = Depends(get_db)) -> CompanyOut:
    company = await CompanyService(db).get_for_admin(company_id)
    return CompanyOut.model_validate(company)


@router.post(
    "", response_model=CompanyOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_CAN_WRITE)]
)
async def create_company(payload: CompanyCreate, db: AsyncSession = Depends(get_db)) -> CompanyOut:
    company = await CompanyService(db).create(payload)
    return CompanyOut.model_validate(company)


@router.put("/{company_id}", response_model=CompanyOut, dependencies=[Depends(_CAN_WRITE)])
async def update_company(
    company_id: str, payload: CompanyUpdate, db: AsyncSession = Depends(get_db)
) -> CompanyOut:
    company = await CompanyService(db).update(company_id, payload)
    return CompanyOut.model_validate(company)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))],
)
async def delete_company(company_id: str, db: AsyncSession = Depends(get_db)) -> None:
    await CompanyService(db).delete(company_id)
