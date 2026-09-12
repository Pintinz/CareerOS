from collections.abc import Callable, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.jwt import InvalidTokenError, TokenAudience, TokenType, decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        decoded = decode_token(credentials.credentials, TokenType.ACCESS, TokenAudience.ADMIN)
    except InvalidTokenError as exc:
        raise unauthorized from exc

    admin = await AdminUserRepository(db).get_by_id(decoded.subject)
    if admin is None or not admin.is_active:
        raise unauthorized

    return admin


def require_admin_role(*allowed_roles: AdminRole) -> Callable:
    """Dependency factory: `Depends(require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN))`.
    Every admin route should specify the roles it accepts explicitly rather than only checking
    "is some kind of admin" (spec §4 RBAC)."""

    async def _check(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        if admin.role not in _as_set(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(r.value for r in allowed_roles)}",
            )
        return admin

    return _check


def _as_set(roles: Iterable[AdminRole]) -> set[AdminRole]:
    return set(roles)
