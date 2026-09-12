from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse
from app.security.jwt import InvalidTokenError, TokenType, create_access_token, create_refresh_token, decode_token
from app.security.password import hash_password, verify_password


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.profiles = ProfileRepository(db)

    async def register(self, *, email: str, password: str) -> User:
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists"
            )

        user = await self.users.create(email=email, hashed_password=hash_password(password))
        await self.profiles.create_empty(user.id)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        invalid_credentials = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )

        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise invalid_credentials
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

        return user

    def issue_tokens(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            user_id = decode_token(refresh_token, TokenType.REFRESH)
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
            ) from exc

        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        return self.issue_tokens(user)

    async def delete_account(self, user: User) -> None:
        await self.users.delete(user)
        await self.db.commit()
