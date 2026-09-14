"""External URL validation for everything discovery fetches, stores or shows (spec §59).

Two different questions, deliberately separate:

- `validate_public_url` — is this URL safe to *store and show a user* (an Apply link, a source
  link)? http(s) only, no credentials, no javascript:/file:/data:, no local hostnames.
- `ensure_fetchable` — may the backend *request* it? Everything above, plus the host must not
  resolve to a private, loopback, link-local or otherwise internal address (SSRF defence — a
  registered source, a redirect or an AI-suggested URL could otherwise point at cloud metadata or
  internal services). Checked for the initial URL and again for every redirect hop.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_URL_LENGTH = 1024
_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata.google.internal", "metadata"}
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa")

# Tracking parameters stripped when canonicalizing, so the same listing shared with different
# campaign tags deduplicates.
_TRACKING_PARAMS = {
    "gh_src", "gh_jid_src", "lever-source", "lever-origin", "source", "src", "ref", "referrer",
    "trk", "trackingid", "fbclid", "gclid", "mc_cid", "mc_eid",
}


class UnsafeUrlError(ValueError):
    """The URL must not be stored, shown, or fetched."""


Resolver = Callable[[str], Awaitable[list[str]]]


def validate_public_url(url: str | None, *, require_https: bool = False) -> str:
    if url is None:
        raise UnsafeUrlError("missing URL")
    candidate = url.strip()
    if not candidate or len(candidate) > MAX_URL_LENGTH:
        raise UnsafeUrlError("URL is empty or too long")
    if any(ch in candidate for ch in ("\x00", "\n", "\r", "\t", " ", "\\")):
        raise UnsafeUrlError("URL contains whitespace or control characters")
    parts = urlsplit(candidate)
    scheme = parts.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme '{scheme or '(none)'}' is not allowed")
    if require_https and scheme != "https":
        raise UnsafeUrlError("HTTPS is required")
    if parts.username or parts.password:
        raise UnsafeUrlError("URLs with embedded credentials are not allowed")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise UnsafeUrlError("URL has no host")
    if host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_SUFFIXES):
        raise UnsafeUrlError("local hostnames are not allowed")
    literal = _parse_ip(host)
    if literal is not None and not literal.is_global:
        raise UnsafeUrlError("non-public IP addresses are not allowed")
    if literal is None and "." not in host:
        raise UnsafeUrlError("single-label hostnames are not allowed")
    return candidate


def _parse_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


async def default_resolver(host: str) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


async def ensure_fetchable(url: str, *, resolver: Resolver | None = None) -> str:
    """Raises UnsafeUrlError unless every address the host resolves to is public."""
    validated = validate_public_url(url)
    host = (urlsplit(validated).hostname or "").lower()
    if _parse_ip(host) is not None:
        return validated  # a literal public IP was already checked above
    try:
        addresses = await (resolver or default_resolver)(host)
    except OSError as exc:
        raise UnsafeUrlError(f"host could not be resolved: {host}") from exc
    if not addresses:
        raise UnsafeUrlError(f"host could not be resolved: {host}")
    for address in addresses:
        ip = _parse_ip(address.split("%", 1)[0])
        if ip is None or not ip.is_global:
            raise UnsafeUrlError("host resolves to a non-public address")
    return validated


def host_of(url: str | None) -> str | None:
    if not url:
        return None
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host or None


def registrable_domain(url_or_host: str | None) -> str | None:
    """Best-effort 'site' comparison without a public-suffix list: the last two labels, or three
    for common two-part country suffixes (co.uk, com.ng, …). Good enough to tell `shell.com` from
    `linkedin.com`; not a security boundary."""
    if not url_or_host:
        return None
    host = host_of(url_or_host) if "://" in url_or_host else url_or_host.lower().removeprefix("www.")
    if not host:
        return None
    labels = host.split(".")
    if len(labels) >= 3 and labels[-2] in {"co", "com", "org", "gov", "ac", "edu", "net"} and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def canonicalize_url(url: str) -> str:
    """Stable form for deduplication: lowercase scheme/host, no fragment, no default port, no
    tracking parameters (utm_* and known ATS source tags), no trailing slash on the path."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host if port is None or (scheme, port) in {("http", 80), ("https", 443)} else f"{host}:{port}"
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, urlencode(sorted(query)), ""))


# Tier-4 discovery-only domains: may help find something, never become the canonical source.
AGGREGATOR_DOMAINS = frozenset({
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com", "monster.com", "simplyhired.com",
    "jobberman.com", "myjobmag.com", "careerbuilder.com", "jooble.org", "adzuna.com", "talent.com",
    "scholars4dev.com", "opportunitiesforafricans.com", "scholarshipdb.net", "facebook.com", "x.com",
    "twitter.com", "instagram.com", "t.me", "whatsapp.com",
})


def is_aggregator_url(url: str | None) -> bool:
    domain = registrable_domain(url)
    return domain in AGGREGATOR_DOMAINS if domain else False


# Public ATS hosts an official employer listing may legitimately live on.
ATS_DOMAINS = frozenset({
    "lever.co", "greenhouse.io", "ashbyhq.com", "smartrecruiters.com", "myworkdayjobs.com", "workday.com",
    "successfactors.com", "successfactors.eu", "sapsf.com", "sapsf.eu", "oraclecloud.com", "taleo.net",
    "icims.com", "jobvite.com", "workable.com", "recruitee.com", "bamboohr.com", "teamtailor.com", "breezy.hr",
})


def is_ats_url(url: str | None) -> bool:
    domain = registrable_domain(url)
    return domain in ATS_DOMAINS if domain else False
