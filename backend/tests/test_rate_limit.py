import pytest
from httpx import AsyncClient

from app.security.rate_limit import reset_all_rate_limiters

pytestmark = pytest.mark.asyncio


async def test_login_is_rate_limited_after_repeated_failed_attempts(client: AsyncClient) -> None:
    """Phase 11 §84-85: protects login against brute force without permanently locking anyone
    out — the limit is a sliding window, not a ban."""
    reset_all_rate_limiters()
    for _ in range(10):
        response = await client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
        assert response.status_code == 401

    limited = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert limited.status_code == 429


async def test_register_is_rate_limited_separately_from_login(client: AsyncClient) -> None:
    reset_all_rate_limiters()
    for i in range(5):
        response = await client.post(
            "/api/v1/auth/register", json={"email": f"rl-{i}@example.com", "password": "candidatepass1"}
        )
        assert response.status_code == 201

    limited = await client.post(
        "/api/v1/auth/register", json={"email": "rl-overflow@example.com", "password": "candidatepass1"}
    )
    assert limited.status_code == 429
