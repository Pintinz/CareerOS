"""Shared fixtures for discovery tests. Every source response here is a MOCK modelled on the public
API shape of the named provider — no test in this suite contacts a real website."""

from __future__ import annotations

import json
from collections.abc import Callable
from xml.sax.saxutils import escape

import httpx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.ingestion.http_client import DiscoveryHttpClient
from app.models.admin_user import AdminRole
from app.repositories.admin_user_repository import AdminUserRepository
from app.security.password import hash_password


async def public_resolver(host: str) -> list[str]:
    return ["93.184.216.34"]


async def no_sleep(_seconds: float) -> None:
    return None


class Router:
    """Maps (method, path-prefix) to handlers; records every request for assertions."""

    def __init__(self) -> None:
        self.routes: list[tuple[str, str, Callable[[httpx.Request], httpx.Response]]] = []
        self.requests: list[httpx.Request] = []

    def add(self, method: str, url_prefix: str, handler) -> Router:
        if not callable(handler):
            response = handler
            handler = lambda request, response=response: response  # noqa: E731
        self.routes.append((method, url_prefix, handler))
        return self

    def json(self, method: str, url_prefix: str, payload, status: int = 200, headers: dict | None = None) -> Router:
        return self.add(method, url_prefix, lambda request: httpx.Response(status, json=payload, headers=headers))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if request.url.path == "/robots.txt" and not any(prefix.endswith("/robots.txt") for _, prefix, _ in self.routes):
            return httpx.Response(404)
        for method, prefix, handler in reversed(self.routes):
            if request.method == method and url.startswith(prefix):
                return handler(request)
        return httpx.Response(404, text="not found")


def make_client(router: Router, **overrides) -> DiscoveryHttpClient:
    options = dict(user_agent="CareerOSDiscoveryBot/test", transport=httpx.MockTransport(router), resolver=public_resolver, sleep=no_sleep, min_interval_seconds=0)
    options.update(overrides)
    return DiscoveryHttpClient(**options)


def discovery_settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        web_discovery_enabled=True,
        auto_publish_discovery=False,
        ai_research_enabled=False,
        anthropic_research_enabled=False,
        discovery_min_request_interval_seconds=0,
    )
    base.update(overrides)
    return Settings(**base)


async def create_admin(db: AsyncSession, *, email: str = "admin@example.com", role: AdminRole = AdminRole.ADMIN) -> None:
    await AdminUserRepository(db).create(email=email, hashed_password=hash_password("adminpass1"), role=role)
    await db.commit()


async def admin_headers(client: AsyncClient, email: str = "admin@example.com") -> dict:
    response = await client.post("/api/v1/admin/auth/login", json={"email": email, "password": "adminpass1"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def user_headers(client: AsyncClient, email: str = "candidate@example.com") -> dict:
    response = await client.post("/api/v1/auth/register", json={"email": email, "password": "candidatepass1"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_company(client: AsyncClient, headers: dict, name: str = "Acme Energy", **fields) -> str:
    response = await client.post("/api/v1/admin/companies", headers=headers, json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def create_source(client: AsyncClient, headers: dict, **fields) -> dict:
    response = await client.post("/api/v1/admin/sources", headers=headers, json=fields)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------------------------------
# Mock provider payloads (shapes follow each provider's public job-board API)
# --------------------------------------------------------------------------------------------------

def lever_posting(posting_id: str, title: str, **overrides) -> dict:
    posting = {
        "id": posting_id,
        "text": title,
        "hostedUrl": f"https://jobs.lever.co/acme/{posting_id}",
        "applyUrl": f"https://jobs.lever.co/acme/{posting_id}/apply",
        "createdAt": 1_788_000_000_000,
        "categories": {"commitment": "Full-time", "department": "Operations", "location": "Lagos, Nigeria"},
        "country": "NG",
        "workplaceType": "onsite",
        "descriptionPlain": f"Acme Energy is hiring a {title}.\n\nYou will keep the plant running.",
        "lists": [
            {"text": "Requirements", "content": "<li>HND or B.Sc in engineering</li><li>Knowledge of PLC systems</li>"},
            {"text": "Responsibilities", "content": "<li>Operate process units</li>"},
        ],
    }
    posting.update(overrides)
    return posting


def greenhouse_job(job_id: int, title: str, **overrides) -> dict:
    job = {
        "id": job_id,
        "title": title,
        "requisition_id": f"REQ-{job_id}",
        "updated_at": "2026-09-10T10:00:00Z",
        "first_published": "2026-09-01T09:00:00Z",
        "location": {"name": "Lagos, Nigeria"},
        "absolute_url": f"https://boards.greenhouse.io/acme/jobs/{job_id}",
        "content": "&lt;p&gt;Join Acme.&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Maintain compressors&lt;/li&gt;&lt;/ul&gt;&lt;script&gt;alert(1)&lt;/script&gt;",
        "departments": [{"name": "Maintenance"}],
    }
    job.update(overrides)
    return job


def job_posting_page(title: str, *, valid_through: str, identifier: str = "ACME-001", extra_html: str = "") -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": f"<p>{title} at Acme Energy.</p><ul><li>Maintain instrumentation</li></ul>",
        "datePosted": "2026-09-01",
        "validThrough": valid_through,
        "employmentType": "FULL_TIME",
        "identifier": {"@type": "PropertyValue", "name": "Acme", "value": identifier},
        "hiringOrganization": {"@type": "Organization", "name": "Acme Energy"},
        "jobLocation": {"@type": "Place", "address": {"addressLocality": "Port Harcourt", "addressCountry": "NG"}},
        "url": f"https://careers.acme-energy.com/jobs/{identifier}",
    }
    return f"""<html><head><title>{title}</title><script type="application/ld+json">{json.dumps(data)}</script></head>
    <body><h1>{title}</h1>{extra_html}</body></html>"""


def rss_feed(items: list[tuple[str, str, str]]) -> str:
    entries = "".join(
        f"<item><title>{escape(title)}</title><link>{escape(link)}</link><guid>{escape(link)}</guid>"
        f"<pubDate>Mon, 07 Sep 2026 09:00:00 GMT</pubDate><description>{escape(summary)}</description></item>"
        for title, link, summary in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>Acme Newsroom</title>{entries}</channel></rss>'
