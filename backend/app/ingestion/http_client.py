"""The only way discovery code talks to the web (spec §5, §31, §59, §61).

Guarantees, in one place:
- every URL (and every redirect hop) passes `ensure_fetchable` — no internal addresses;
- robots.txt is honoured for our user agent; an unreachable robots.txt (5xx/network) fails closed;
- requests to one host are spaced by a minimum interval, and a run has a hard request budget;
- 429 honours Retry-After: a short wait is retried once, a long one stops the run as RATE_LIMITED;
- 5xx/network errors retry with bounded backoff; 4xx are permanent and never retried;
- 401/403 mean "access controlled" — reported as FETCH_FAILED, never worked around;
- response bodies are size-capped while streaming;
- logs carry only host, status, duration and size — never headers, cookies or bodies.

It sends no credentials and no cookies: discovery only reads public pages and public APIs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.ingestion.url_safety import Resolver, UnsafeUrlError, ensure_fetchable

logger = logging.getLogger("careeros.discovery.http")

MAX_REDIRECTS = 5
MAX_RETRY_AFTER_WAIT_SECONDS = 10.0
MAX_TRANSIENT_ATTEMPTS = 3


class FetchError(Exception):
    """Base class. `code` is a short stable identifier stored on sources/runs (never a message
    containing a URL query string or response body)."""

    code = "FETCH_ERROR"
    permanent = False

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RobotsDisallowedError(FetchError):
    code = "ROBOTS_DISALLOWED"
    permanent = True


class AccessDeniedError(FetchError):
    code = "ACCESS_DENIED"  # 401/403 — login walls, anti-bot: never bypassed
    permanent = True


class NotFoundError(FetchError):
    code = "NOT_FOUND"  # 404/410
    permanent = True


class ClientRequestError(FetchError):
    code = "CLIENT_ERROR"
    permanent = True


class RateLimitedError(FetchError):
    code = "RATE_LIMITED"

    def __init__(self, message: str, *, retry_after_seconds: float | None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after_seconds = retry_after_seconds


class ServerError(FetchError):
    code = "SERVER_ERROR"


class NetworkError(FetchError):
    code = "NETWORK_ERROR"


class ResponseTooLargeError(FetchError):
    code = "RESPONSE_TOO_LARGE"
    permanent = True


class UnsafeTargetError(FetchError):
    code = "UNSAFE_URL"
    permanent = True


class RequestBudgetExceededError(FetchError):
    code = "REQUEST_BUDGET_EXCEEDED"
    permanent = True


class InvalidResponseError(FetchError):
    code = "INVALID_RESPONSE"
    permanent = True


@dataclass
class FetchedResponse:
    url: str  # final URL after redirects
    status_code: int
    content_type: str
    body: bytes
    redirected: bool = False
    elapsed_ms: int = 0

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        try:
            return json.loads(self.body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidResponseError("response is not valid JSON") from exc


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - (now or datetime.now(timezone.utc))).total_seconds())


@dataclass
class _RobotsEntry:
    parser: RobotFileParser | None  # None = allow all (robots.txt absent)
    disallow_all: bool
    fetched_at: float


class HostThrottle:
    """Process-wide minimum spacing between requests to the same host."""

    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def wait(self, host: str, *, sleep: Callable[[float], Awaitable[None]], clock: Callable[[], float]) -> None:
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            last = self._last.get(host)
            if last is not None:
                remaining = self.min_interval_seconds - (clock() - last)
                if remaining > 0:
                    await sleep(remaining)
            self._last[host] = clock()


_ROBOTS_TTL_SECONDS = 6 * 3600
_robots_cache: dict[str, _RobotsEntry] = {}
_shared_throttle: HostThrottle | None = None


def reset_http_state() -> None:
    """Tests only: forget cached robots.txt decisions and host timing."""
    global _shared_throttle
    _robots_cache.clear()
    _shared_throttle = None


@dataclass
class DiscoveryHttpClient:
    user_agent: str
    timeout_seconds: float = 20.0
    max_response_bytes: int = 3_000_000
    max_requests: int = 60
    min_interval_seconds: float = 2.0
    transport: httpx.AsyncBaseTransport | None = None
    resolver: Resolver | None = None
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    clock: Callable[[], float] = time.monotonic
    respect_robots: bool = True
    # Verify TLS against the operating system's certificate store instead of certifi's bundle — for
    # networks whose TLS-inspecting proxy or antivirus installs its own root. Verification stays on.
    use_system_trust_store: bool = False
    requests_made: int = 0
    stats: dict = field(default_factory=lambda: {"requests": 0, "retries": 0, "bytes": 0, "hosts": {}})

    def __post_init__(self) -> None:
        global _shared_throttle
        if _shared_throttle is None or _shared_throttle.min_interval_seconds != self.min_interval_seconds:
            _shared_throttle = HostThrottle(self.min_interval_seconds)
        self._throttle = _shared_throttle
        verify: bool | ssl.SSLContext = True
        if self.use_system_trust_store and self.transport is None:
            import truststore  # lazy: only needed when enabled

            verify = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._client = httpx.AsyncClient(
            transport=self.transport,
            verify=verify,
            timeout=httpx.Timeout(self.timeout_seconds),
            follow_redirects=False,  # every hop is validated by hand
            headers={"User-Agent": self.user_agent, "Accept-Language": "en"},
            cookies=None,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> DiscoveryHttpClient:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    # ------------------------------------------------------------------------------------------
    async def get_json(self, url: str, *, params: dict | None = None):
        response = await self.fetch(url, params=params, accept="application/json")
        return response.json()

    async def post_json(self, url: str, payload: dict):
        response = await self.fetch(url, method="POST", json_body=payload, accept="application/json")
        return response.json()

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        params: dict | None = None,
        json_body: dict | None = None,
        accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        check_robots: bool = True,
    ) -> FetchedResponse:
        attempt = 0
        while True:
            attempt += 1
            try:
                return await self._fetch_once(url, method=method, params=params, json_body=json_body, accept=accept, check_robots=check_robots)
            except RateLimitedError as exc:
                wait = exc.retry_after_seconds
                if attempt == 1 and wait is not None and wait <= MAX_RETRY_AFTER_WAIT_SECONDS:
                    self.stats["retries"] += 1
                    await self.sleep(wait)
                    continue
                raise
            except (ServerError, NetworkError):
                if attempt >= MAX_TRANSIENT_ATTEMPTS:
                    raise
                self.stats["retries"] += 1
                await self.sleep(min(30.0, 1.5 * (2 ** (attempt - 1))))

    async def _fetch_once(self, url, *, method, params, json_body, accept, check_robots) -> FetchedResponse:
        current = url
        redirected = False
        for _hop in range(MAX_REDIRECTS + 1):
            try:
                current = await ensure_fetchable(current, resolver=self.resolver)
            except UnsafeUrlError as exc:
                raise UnsafeTargetError(str(exc)) from exc
            if check_robots and self.respect_robots:
                await self._check_robots(current)

            if self.requests_made >= self.max_requests:
                raise RequestBudgetExceededError("request budget for this run is used up")
            host = urlsplit(current).hostname or ""
            await self._throttle.wait(host, sleep=self.sleep, clock=self.clock)
            self.requests_made += 1
            self.stats["requests"] += 1
            self.stats["hosts"][host] = self.stats["hosts"].get(host, 0) + 1

            started = self.clock()
            try:
                request = self._client.build_request(
                    method, current, params=params if not redirected else None, json=json_body, headers={"Accept": accept}
                )
                response = await self._client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                raise NetworkError("request timed out") from exc
            except httpx.HTTPError as exc:
                raise NetworkError(f"network error ({type(exc).__name__})") from exc

            self.stats["last_status"] = response.status_code
            try:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location:
                        raise InvalidResponseError("redirect without a Location header", status_code=response.status_code)
                    current = urljoin(str(response.request.url), location)
                    redirected = True
                    if response.status_code == 303:
                        method, json_body = "GET", None
                    continue
                body = await self._read_capped(response)
            finally:
                await response.aclose()

            elapsed_ms = int((self.clock() - started) * 1000)
            logger.info(
                "discovery_fetch host=%s status=%s bytes=%s ms=%s", host, response.status_code, len(body), elapsed_ms
            )
            self._raise_for_status(response)
            return FetchedResponse(
                url=str(response.request.url),
                status_code=response.status_code,
                content_type=response.headers.get("content-type", ""),
                body=body,
                redirected=redirected,
                elapsed_ms=elapsed_ms,
            )
        raise InvalidResponseError("too many redirects")

    async def _read_capped(self, response: httpx.Response) -> bytes:
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > self.max_response_bytes:
            raise ResponseTooLargeError("response exceeds the size limit")
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self.max_response_bytes:
                raise ResponseTooLargeError("response exceeds the size limit")
            chunks.append(chunk)
        self.stats["bytes"] += size
        return b"".join(chunks)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        code = response.status_code
        if code < 400:
            return
        if code == 429:
            raise RateLimitedError("rate limited by source", retry_after_seconds=parse_retry_after(response.headers.get("retry-after")))
        if code in (401, 403):
            raise AccessDeniedError("source requires authorization or blocks automated access", status_code=code)
        if code in (404, 410):
            raise NotFoundError("not found at source", status_code=code)
        if code >= 500:
            raise ServerError(f"source returned {code}", status_code=code)
        raise ClientRequestError(f"source returned {code}", status_code=code)

    async def _check_robots(self, url: str) -> None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        entry = _robots_cache.get(origin)
        if entry is None or self.clock() - entry.fetched_at > _ROBOTS_TTL_SECONDS:
            entry = await self._load_robots(origin)
            _robots_cache[origin] = entry
        if entry.disallow_all:
            raise RobotsDisallowedError("robots.txt could not be read; not fetching (fail closed)")
        if entry.parser is not None and not entry.parser.can_fetch(self.user_agent, url):
            raise RobotsDisallowedError("disallowed by robots.txt")

    async def _load_robots(self, origin: str) -> _RobotsEntry:
        try:
            response = await self._fetch_once(
                f"{origin}/robots.txt", method="GET", params=None, json_body=None, accept="text/plain", check_robots=False
            )
        except (NotFoundError, AccessDeniedError, ClientRequestError):
            # RFC 9309: a 4xx robots.txt means no restrictions.
            return _RobotsEntry(parser=None, disallow_all=False, fetched_at=self.clock())
        except FetchError:
            return _RobotsEntry(parser=None, disallow_all=True, fetched_at=self.clock())
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return _RobotsEntry(parser=parser, disallow_all=False, fetched_at=self.clock())


def backoff_until(*, consecutive_failures: int, interval_minutes: int, now: datetime | None = None) -> datetime:
    """Exponential source-level backoff after repeated failures, capped at 7 days."""
    now = now or datetime.now(timezone.utc)
    minutes = min(interval_minutes * (2 ** max(0, consecutive_failures - 1)), 7 * 24 * 60)
    return now + timedelta(minutes=minutes)
