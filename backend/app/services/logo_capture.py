"""Organization logos captured from an official website into CareerOS media storage.

Logos are never hotlinked: the image is fetched once through the discovery HTTP client (robots.txt,
SSRF checks, size limits), decoded and re-encoded with Pillow as a square PNG, and stored like any
admin upload (a `MediaAsset`). An admin triggers it and can replace or clear the result.

Candidates, best first: the site's declared brand icons (`apple-touch-icon`, large PNG `icon`
links), a schema.org Organization `logo`, then `/apple-touch-icon.png` and `/favicon.ico`. SVG is
skipped — it can carry scripts and Pillow can't rasterize it — so a site offering only SVG yields
"no usable logo" and the admin uploads one instead.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from lxml import html as lxml_html
from lxml.etree import ParserError
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings, get_settings
from app.ingestion.http_client import DiscoveryHttpClient, FetchError
from app.ingestion.url_safety import UnsafeUrlError, validate_public_url

MAX_LOGO_BYTES = 2_000_000
MAX_SOURCE_DIMENSION = 4096
MIN_LOGO_PX = 48
OUTPUT_PX = 256
MAX_CANDIDATES = 6
_RASTER_TYPES = ("image/png", "image/jpeg", "image/webp", "image/x-icon", "image/vnd.microsoft.icon", "image/gif")


class LogoNotFoundError(Exception):
    """No usable raster logo could be found on the website."""


@dataclass(frozen=True)
class CapturedLogo:
    png: bytes
    source_url: str
    width: int
    height: int


def _sizes(value: str | None) -> int:
    match = re.search(r"(\d+)\s*x\s*(\d+)", value or "", re.I)
    return int(match.group(1)) if match else 0


def logo_candidates(markup: str, page_url: str) -> list[str]:
    """Ordered candidate image URLs declared by the page. Untrusted markup: only link/meta
    attributes and JSON-LD `logo` values are read, and every URL is validated before use."""
    try:
        root = lxml_html.fromstring(markup[:2_000_000])
    except (ParserError, ValueError):
        root = None
    scored: list[tuple[int, str]] = []
    if root is not None:
        for link in root.xpath("//link[@rel][@href]")[:200]:
            rel = (link.get("rel") or "").lower().split()
            href = link.get("href") or ""
            if href.lower().split("?")[0].endswith(".svg") or (link.get("type") or "").lower() == "image/svg+xml":
                continue
            size = _sizes(link.get("sizes"))
            if "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel:
                scored.append((1000 + size, href))
            elif "icon" in rel and (size >= 96 or href.lower().split("?")[0].endswith(".png")):
                scored.append((500 + size, href))
        for script in root.xpath('//script[@type="application/ld+json"]')[:20]:
            try:
                data = json.loads((script.text or "")[:200_000])
            except ValueError:
                continue
            stack = [data]
            while stack:
                node = stack.pop()
                if isinstance(node, list):
                    stack.extend(node[:50])
                elif isinstance(node, dict):
                    types = node.get("@type")
                    types = {str(t) for t in types} if isinstance(types, list) else {str(types)}
                    logo = node.get("logo")
                    if logo and types & {"Organization", "Corporation", "NGO", "EducationalOrganization", "GovernmentOrganization", "CollegeOrUniversity", "WebSite"}:
                        url = logo.get("url") or logo.get("contentUrl") if isinstance(logo, dict) else logo
                        if isinstance(url, str) and not url.lower().split("?")[0].endswith(".svg"):
                            scored.append((800, url))
                    stack.extend(v for k, v in node.items() if k in ("@graph", "publisher", "author", "brand"))
    scored.sort(key=lambda pair: -pair[0])
    ordered = [href for _, href in scored] + ["/apple-touch-icon.png", "/favicon.ico"]
    seen: list[str] = []
    for href in ordered:
        try:
            absolute = validate_public_url(urljoin(page_url, href.strip()))
        except UnsafeUrlError:
            continue
        if absolute not in seen:
            seen.append(absolute)
    return seen[:MAX_CANDIDATES]


def normalize_logo(data: bytes) -> tuple[bytes, int, int]:
    """Decode an untrusted image and re-encode it as a square transparent PNG. Raises ValueError
    for anything that isn't a reasonably sized raster image."""
    if len(data) > MAX_LOGO_BYTES:
        raise ValueError("image too large")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        image = Image.open(io.BytesIO(data))
        if image.format == "ICO":
            # Pick the largest embedded icon.
            sizes = sorted(image.info.get("sizes") or [image.size], key=lambda s: s[0] * s[1])
            image.size = sizes[-1]
        if image.width > MAX_SOURCE_DIMENSION or image.height > MAX_SOURCE_DIMENSION:
            raise ValueError("image dimensions too large")
        image.load()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError("not a valid raster image") from exc
    if min(image.size) < MIN_LOGO_PX:
        raise ValueError("image too small to use as a logo")
    image = image.convert("RGBA")
    side = max(image.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    if side > OUTPUT_PX:
        canvas = canvas.resize((OUTPUT_PX, OUTPUT_PX), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue(), canvas.width, canvas.height


def default_client(settings: Settings | None = None) -> DiscoveryHttpClient:
    s = settings or get_settings()
    return DiscoveryHttpClient(
        user_agent=s.discovery_user_agent, timeout_seconds=s.discovery_request_timeout_seconds,
        max_response_bytes=s.discovery_max_response_bytes, max_requests=MAX_CANDIDATES + 2, min_interval_seconds=0.5,
        use_system_trust_store=s.outbound_tls_trust_store == "system",
    )


def get_logo_client_factory():
    """FastAPI dependency (overridden in tests with a mock transport)."""
    return default_client


async def capture_logo(website_url: str, *, client: DiscoveryHttpClient) -> CapturedLogo:
    page_url = validate_public_url(website_url)
    try:
        page = await client.fetch(page_url)
        candidates = logo_candidates(page.text, page.url)
    except FetchError:
        candidates = logo_candidates("", page_url)
    for candidate in candidates:
        try:
            response = await client.fetch(candidate, accept="image/png,image/webp,image/jpeg;q=0.9,image/*;q=0.5")
        except FetchError:
            continue
        content_type = (response.content_type or "").split(";")[0].strip().lower()
        if content_type and content_type not in _RASTER_TYPES and not content_type.startswith("application/octet-stream"):
            continue
        try:
            png, width, height = normalize_logo(response.body)
        except ValueError:
            continue
        return CapturedLogo(png=png, source_url=response.url, width=width, height=height)
    raise LogoNotFoundError(
        "No usable logo (PNG, JPEG, WebP or ICO, at least 48px) was found on this website. Upload one in Media and paste its URL."
    )
