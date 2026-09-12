from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.security.jwt import InvalidTokenError, TokenType, decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        decoded = decode_token(credentials.credentials, TokenType.ACCESS)
    except InvalidTokenError as exc:
        raise unauthorized from exc

    user = await UserRepository(db).get_by_id(decoded.subject)
    if user is None or not user.is_active:
        raise unauthorized

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """For public endpoints that personalize when a valid token is present (e.g. is_saved on
    a job card) but must still work for anonymous browsing. Never raises — an invalid/expired
    token is treated the same as no token, not an error."""
    if credentials is None:
        return None
    try:
        decoded = decode_token(credentials.credentials, TokenType.ACCESS)
    except InvalidTokenError:
        return None

    user = await UserRepository(db).get_by_id(decoded.subject)
    if user is None or not user.is_active:
        return None
    return user
