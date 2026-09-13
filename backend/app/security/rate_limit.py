"""Minimal in-memory rate limiting for auth-adjacent endpoints (Phase 11, spec §84-85).

Deliberately dependency-free (no Redis) — this project has no Redis/Celery deployment in this
environment (see DEPLOYMENT.md). **Known limitation, documented rather than hidden**: this is
per-process state, so it only actually limits abuse against a single backend instance; a
multi-instance production deployment needs a shared store (Redis `INCR`+`EXPIRE` is the standard
choice) for this to be meaningful at scale — see RELEASE_READINESS.md. Still real and effective
for the common single-instance-or-low-scale case, and strictly better than no limiting at all.

Never locks a legitimate user out permanently (spec §85): the window slides and always clears.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _key(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"
        return f"{request.url.path}:{client_ip}"

    def check(self, request: Request) -> None:
        now = time.monotonic()
        key = self._key(request)
        window_start = now - self.window_seconds
        recent = [t for t in self._hits[key] if t > window_start]
        if len(recent) >= self.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait a few minutes and try again.",
            )
        recent.append(now)
        self._hits[key] = recent


# Shared instances — one per sensitive endpoint category, tuned conservatively (spec §85: protect
# without locking out legitimate users). FastAPI dependency usage: `Depends(login_rate_limiter)`.
_login_limiter = RateLimiter(max_attempts=10, window_seconds=300)
_register_limiter = RateLimiter(max_attempts=5, window_seconds=300)
_admin_login_limiter = RateLimiter(max_attempts=10, window_seconds=300)


def reset_all_rate_limiters() -> None:
    """Test-only: each test in this codebase's suite creates fresh users/admins against a shared
    in-process limiter, so without a reset a long test run would eventually trip a 429 on a
    perfectly legitimate test — see `tests/conftest.py`'s autouse fixture."""
    for limiter in (_login_limiter, _register_limiter, _admin_login_limiter):
        limiter._hits.clear()


def login_rate_limit(request: Request) -> None:
    _login_limiter.check(request)


def register_rate_limit(request: Request) -> None:
    _register_limiter.check(request)


def admin_login_rate_limit(request: Request) -> None:
    _admin_login_limiter.check(request)
