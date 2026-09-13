from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from app.security.dependencies import get_current_user
from app.security.rate_limit import login_rate_limit, register_rate_limit
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limit)],
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    user = await service.register(email=payload.email, password=payload.password)
    return service.issue_tokens(user)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_rate_limit)])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    user = await service.authenticate(email=payload.email, password=payload.password)
    return service.issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await AuthService(db).delete_account(current_user)
