import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str = "jane@example.com", password: str = "supersecret1"):
    return await client.post("/api/v1/auth/register", json={"email": email, "password": password})


async def test_register_returns_tokens(client: AsyncClient) -> None:
    response = await _register(client)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_register_duplicate_email_rejected(client: AsyncClient) -> None:
    await _register(client)
    response = await _register(client)
    assert response.status_code == 409


async def test_login_with_correct_credentials(client: AsyncClient) -> None:
    await _register(client, "login@example.com", "correcthorse1")
    response = await client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "correcthorse1"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_with_wrong_password_rejected(client: AsyncClient) -> None:
    await _register(client, "wrong@example.com", "correcthorse1")
    response = await client.post(
        "/api/v1/auth/login", json={"email": "wrong@example.com", "password": "incorrect"}
    )
    assert response.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient) -> None:
    register_response = await _register(client, "me@example.com", "correcthorse1")
    token = register_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_profile_created_empty_on_register_and_updatable(client: AsyncClient) -> None:
    register_response = await _register(client, "profile@example.com", "correcthorse1")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    get_response = await client.get("/api/v1/profile", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["full_name"] is None

    put_response = await client.put(
        "/api/v1/profile", headers=headers, json={"full_name": "Jane Doe", "location": "Lagos, Nigeria"}
    )
    assert put_response.status_code == 200
    body = put_response.json()
    assert body["full_name"] == "Jane Doe"
    assert body["location"] == "Lagos, Nigeria"


async def test_refresh_token_issues_new_access_token(client: AsyncClient) -> None:
    register_response = await _register(client, "refresh@example.com", "correcthorse1")
    refresh_token = register_response.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_delete_account(client: AsyncClient) -> None:
    register_response = await _register(client, "delete@example.com", "correcthorse1")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    delete_response = await client.delete("/api/v1/auth/me", headers=headers)
    assert delete_response.status_code == 204

    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 401
