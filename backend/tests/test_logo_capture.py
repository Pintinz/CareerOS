"""Organization logo capture from an official website. All websites are mocked."""

import io

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.http_client import reset_http_state
from app.main import app
from app.models.admin_ops import AuditLog
from app.models.media import MediaAsset
from app.services.logo_capture import get_logo_client_factory, logo_candidates, normalize_logo
from tests.discovery_support import Router, admin_headers, create_admin, make_client

pytestmark = pytest.mark.asyncio


def png_bytes(width: int, height: int, color=(20, 110, 240, 255)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _fresh_http_state():
    reset_http_state()
    yield
    reset_http_state()
    app.dependency_overrides.pop(get_logo_client_factory, None)


def use_router(router: Router) -> None:
    app.dependency_overrides[get_logo_client_factory] = lambda: (lambda: make_client(router))


async def test_candidates_prefer_declared_brand_icons_and_skip_svg_and_unsafe_urls() -> None:
    markup = """<html><head>
      <link rel="icon" href="/favicon-16.png" sizes="16x16">
      <link rel="icon" type="image/svg+xml" href="/logo.svg">
      <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon-180.png">
      <link rel="icon" href="javascript:alert(1)">
      <script type="application/ld+json">{"@type": "Organization", "logo": {"@type": "ImageObject", "url": "https://cdn.acme.com/logo.png"}}</script>
    </head></html>"""
    candidates = logo_candidates(markup, "https://www.acme.com/")
    assert candidates[0] == "https://www.acme.com/apple-touch-icon-180.png"
    assert candidates[1] == "https://cdn.acme.com/logo.png"
    assert "https://www.acme.com/logo.svg" not in candidates
    assert not any(c.startswith("javascript") for c in candidates)
    assert candidates[-1] == "https://www.acme.com/favicon.ico"


async def test_normalize_makes_a_square_png_and_rejects_unusable_images() -> None:
    data, width, height = normalize_logo(png_bytes(180, 120))
    assert (width, height) == (180, 180)
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "PNG" and image.getpixel((0, 0))[3] == 0  # transparent padding
    assert normalize_logo(png_bytes(1024, 1024))[1:] == (256, 256)
    with pytest.raises(ValueError):
        normalize_logo(png_bytes(16, 16))
    with pytest.raises(ValueError):
        normalize_logo(b"<svg onload='alert(1)'></svg>")


async def test_admin_captures_logo_into_media_storage(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    router = (
        Router()  # later routes win on overlapping prefixes
        .add("GET", "https://www.acme.com/", httpx.Response(200, text='<link rel="apple-touch-icon" href="/apple-touch-icon.png">', headers={"content-type": "text/html"}))
        .add("GET", "https://www.acme.com/apple-touch-icon.png", httpx.Response(200, content=png_bytes(180, 180), headers={"content-type": "image/png"}))
    )
    use_router(router)
    response = await client.post("/api/v1/admin/uploads/image/from-website", headers=headers, json={"website_url": "https://www.acme.com/", "alt_text": "Acme logo"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["url"].startswith("http") and "/uploads/" in body["url"] and body["url"].endswith(".png")
    assert "acme.com" not in body["url"]  # stored copy, not a hotlink
    assert body["source_url"] == "https://www.acme.com/apple-touch-icon.png"
    assert (body["width"], body["height"], body["mime_type"]) == (180, 180, "image/png")
    asset = (await db_session.execute(select(MediaAsset).where(MediaAsset.id == body["media_asset_id"]))).scalar_one()
    assert asset.alt_text == "Acme logo"
    assert (await db_session.execute(select(AuditLog).where(AuditLog.action == "logo_captured"))).scalar_one_or_none() is not None


async def test_site_without_a_raster_logo_is_reported_not_guessed(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_admin(db_session)
    headers = await admin_headers(client)
    router = Router().add("GET", "https://svg-only.example/", httpx.Response(200, text='<link rel="icon" href="/logo.svg">', headers={"content-type": "text/html"}))
    use_router(router)
    response = await client.post("/api/v1/admin/uploads/image/from-website", headers=headers, json={"website_url": "https://svg-only.example/"})
    assert response.status_code == 422
    assert "No usable" in response.json()["detail"]

    private = await client.post("/api/v1/admin/uploads/image/from-website", headers=headers, json={"website_url": "http://127.0.0.1/"})
    assert private.status_code == 422


async def test_logo_capture_requires_an_editor(client: AsyncClient) -> None:
    response = await client.post("/api/v1/admin/uploads/image/from-website", json={"website_url": "https://www.acme.com/"})
    assert response.status_code in (401, 403)


async def test_system_trust_store_is_opt_in(monkeypatch) -> None:
    import truststore

    from app.ingestion.http_client import DiscoveryHttpClient

    created = []
    real = truststore.SSLContext
    monkeypatch.setattr(truststore, "SSLContext", lambda *args: created.append(args) or real(*args))
    await DiscoveryHttpClient(user_agent="test").aclose()
    assert created == []
    await DiscoveryHttpClient(user_agent="test", use_system_trust_store=True).aclose()
    assert len(created) == 1
