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


async def test_account_deletion_removes_every_row_belonging_to_the_user(client: AsyncClient, db_session) -> None:
    """Phase 11 §80-81: store policies and PRIVACY.md promise account deletion removes the user's
    data. Seed data across many user-owned tables, delete the account, and check every table that
    references users — not just that the login stops working."""
    import io

    from sqlalchemy import text

    from app.db.base import Base

    headers = {"Authorization": f"Bearer {(await _register(client, 'erase-me@example.com', 'correcthorse1')).json()['access_token']}"}
    other = {"Authorization": f"Bearer {(await _register(client, 'keep-me@example.com', 'correcthorse1')).json()['access_token']}"}
    user_id = (await client.get("/api/v1/auth/me", headers=headers)).json()["id"]

    app_resp = await client.post(
        "/api/v1/applications", headers=headers, json={"company_name": "Acme", "role_title": "Technician"}
    )
    await client.post(f"/api/v1/applications/{app_resp.json()['id']}/notes", headers=headers, json={"body": "call back"})
    await client.post("/api/v1/applications", headers=other, json={"company_name": "Keep", "role_title": "Kept"})
    await client.post(
        "/api/v1/ats/cv", headers=headers, files={"file": ("cv.txt", io.BytesIO(b"PLC maintenance technician"), "text/plain")}
    )
    await client.post("/api/v1/star-stories", headers=headers, json={"title": "Outage fix", "category": "PROBLEM_SOLVING"})
    await client.post("/api/v1/push/devices", headers=headers, json={"platform": "ANDROID", "token": "tok-erase"})
    await client.put("/api/v1/push/preferences", headers=headers, json={"deadlines": False})
    await client.post(
        "/api/v1/monetization/rewards/claim", headers=headers, json={"reward_type": "EXTRA_ATS_ANALYSIS", "reference_id": "erase-ref"}
    )

    user_tables = [
        (table.name, fk.parent.name)
        for table in Base.metadata.sorted_tables
        for fk in table.foreign_keys
        if fk.column.table.name == "users"
    ]

    async def owned_rows() -> dict[str, int]:
        counts = {}
        for table_name, column in user_tables:
            result = await db_session.execute(text(f'SELECT count(*) FROM "{table_name}" WHERE "{column}" = :uid'), {"uid": user_id})
            counts[table_name] = result.scalar_one()
        return counts

    before = await owned_rows()
    assert sum(before.values()) >= 6, before  # the seeding above actually created user-owned rows

    assert (await client.delete("/api/v1/auth/me", headers=headers)).status_code == 204

    after = await owned_rows()
    assert all(count == 0 for count in after.values()), after
    note_count = (await db_session.execute(text("SELECT count(*) FROM application_notes"))).scalar_one()
    assert note_count == 0  # rows owned indirectly (via the deleted application) are gone too
    # Another user's data is untouched.
    assert (await client.get("/api/v1/applications", headers=other)).json()["total"] == 1


async def test_profile_update_leaves_unsent_fields_untouched(client: AsyncClient) -> None:
    token = (await _register(client, "partial@example.com", "correcthorse1")).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        "/api/v1/profile", headers=headers, json={"full_name": "Ada Obi", "professional_title": "Process Engineer"}
    )
    response = await client.put("/api/v1/profile", headers=headers, json={"location": "Lagos"})

    body = response.json()
    assert body["location"] == "Lagos"
    assert body["full_name"] == "Ada Obi"  # previously wiped to null by a partial update
    assert body["professional_title"] == "Process Engineer"

    cleared = await client.put("/api/v1/profile", headers=headers, json={"professional_title": None})
    assert cleared.json()["professional_title"] is None  # explicit null still clears
