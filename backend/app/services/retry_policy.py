"""Reusable retry/backoff policy for calls to external providers (Phase 9 spec §40, closing a
Phase 8 gap). Every external-provider call in this codebase (Gmail, Outlook, and any future
provider) should route through `run_with_retry` rather than hand-rolling its own retry loop, so the
classification rules and backoff math live in exactly one place.
"""

import asyncio
import random
from dataclasses import dataclass
from enum import Enum

import httpx


class FailureCategory(str, Enum):
    TRANSIENT = "TRANSIENT"  # network timeout, connection error, 429, 5xx — worth retrying.
    AUTHORIZATION = "AUTHORIZATION"  # 401/403 — token is bad; retrying won't help, reauth will.
    CONFIGURATION = "CONFIGURATION"  # missing/invalid provider config — an operator problem.
    INVALID_REQUEST = "INVALID_REQUEST"  # 4xx other than 401/403/429 — a permanent client error.
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"  # explicit 503/504 — transient, but worth a longer wait.
    UNKNOWN = "UNKNOWN"


class PermanentFailure(Exception):
    """Raised by `run_with_retry` when a call fails with a non-retryable category — callers should
    catch this specifically to distinguish "gave up after retries" from "never going to work"."""

    def __init__(self, category: FailureCategory, original: Exception) -> None:
        self.category = category
        self.original = original
        super().__init__(f"{category.value}: {original}")


def classify_exception(exc: Exception) -> FailureCategory:
    if isinstance(exc, httpx.TimeoutException) or isinstance(exc, httpx.ConnectError):
        return FailureCategory.TRANSIENT
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return FailureCategory.AUTHORIZATION
        if status == 429 or status >= 500:
            return FailureCategory.TRANSIENT if status != 503 and status != 504 else FailureCategory.PROVIDER_OUTAGE
        return FailureCategory.INVALID_REQUEST
    return FailureCategory.UNKNOWN


_RETRYABLE = {FailureCategory.TRANSIENT, FailureCategory.PROVIDER_OUTAGE, FailureCategory.UNKNOWN}


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter_fraction: float = 0.25

    def delay_for_attempt(self, attempt: int) -> float:
        """`attempt` is 1-indexed (the delay before the *next* attempt after this failed one)."""
        exponential = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))
        jitter = exponential * self.jitter_fraction
        return exponential + random.uniform(-jitter, jitter)


DEFAULT_RETRY_POLICY = RetryPolicy()


async def run_with_retry(
    func,
    *args,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    classify=classify_exception,
    sleep=asyncio.sleep,
    **kwargs,
):
    """Awaits `func(*args, **kwargs)`, retrying on transient/outage/unknown failures with
    exponential backoff + jitter, up to `policy.max_attempts`. Authorization/configuration/
    invalid-request failures are never retried — they're re-raised immediately as
    `PermanentFailure` so a caller (e.g. the watch-renewal job) can mark the connection
    `REAUTHORIZATION_REQUIRED` instead of burning attempts on a call that can't succeed."""
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — classified immediately below, never swallowed.
            category = classify(exc)
            if category not in _RETRYABLE:
                raise PermanentFailure(category, exc) from exc
            last_exc = exc
            if attempt == policy.max_attempts:
                raise PermanentFailure(category, exc) from exc
            await sleep(policy.delay_for_attempt(attempt))
    raise PermanentFailure(FailureCategory.UNKNOWN, last_exc or RuntimeError("unreachable"))
