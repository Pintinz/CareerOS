from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, NamedTuple

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenAudience(StrEnum):
    """Keeps consumer and admin tokens from ever being interchangeable — a router that
    expects USER must reject an ADMIN token and vice versa (spec §4/§52)."""

    USER = "user"
    ADMIN = "admin"


class InvalidTokenError(Exception):
    pass


class DecodedToken(NamedTuple):
    subject: str
    audience: TokenAudience


def _create_token(
    subject: str, token_type: TokenType, audience: TokenAudience, expires_delta: timedelta
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "aud": audience.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, audience: TokenAudience = TokenAudience.USER) -> str:
    return _create_token(
        subject, TokenType.ACCESS, audience, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str, audience: TokenAudience = TokenAudience.USER) -> str:
    return _create_token(
        subject, TokenType.REFRESH, audience, timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(
    token: str, expected_type: TokenType, expected_audience: TokenAudience = TokenAudience.USER
) -> DecodedToken:
    """Returns (subject, audience) if the token is valid, of the expected type, and issued for
    the expected audience (consumer vs. admin)."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=expected_audience.value,
        )
    except JWTError as exc:
        raise InvalidTokenError("Token is invalid, expired, or issued for a different audience") from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Expected a {expected_type.value} token")

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token missing subject")
    return DecodedToken(subject=subject, audience=TokenAudience(payload["aud"]))
