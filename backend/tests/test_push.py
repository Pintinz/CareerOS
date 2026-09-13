import pytest
from httpx import AsyncClient

from tests.test_jobs import _user_headers

pytestmark = pytest.mark.asyncio


async def test_registering_a_device_token_is_idempotent_and_notification_preferences_default_on(
    client: AsyncClient,
) -> None:
    headers = await _user_headers(client)

    register = await client.post(
        "/api/v1/push/devices", headers=headers, json={"platform": "ANDROID", "token": "fcm-token-123"}
    )
    assert register.status_code == 204

    # Re-registering the same token (spec §30's "token refresh") must not error or duplicate.
    register_again = await client.post(
        "/api/v1/push/devices", headers=headers, json={"platform": "ANDROID", "token": "fcm-token-123"}
    )
    assert register_again.status_code == 204

    prefs = await client.get("/api/v1/push/preferences", headers=headers)
    assert prefs.status_code == 200
    body = prefs.json()
    # Every category defaults to enabled (spec §31) — a user who never visits settings still
    # gets everything, never silently opted out.
    assert all(body.values())


async def test_a_category_can_be_disabled_without_affecting_others(client: AsyncClient) -> None:
    headers = await _user_headers(client)

    update = await client.put(
        "/api/v1/push/preferences", headers=headers, json={"deadlines": False}
    )
    assert update.status_code == 200
    body = update.json()
    assert body["deadlines"] is False
    assert body["application_updates"] is True


async def test_unregistering_a_device_token_does_not_error_for_an_unknown_token(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    response = await client.delete("/api/v1/push/devices/never-registered-token", headers=headers)
    assert response.status_code == 204
