import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ats_analysis import AtsAnalysis
from app.models.admin_user import AdminRole
from tests.test_aptitude import _create_session, _seed_numerical_bank
from tests.test_jobs import _admin_headers, _create_admin, _user_headers

pytestmark = pytest.mark.asyncio


async def _current_user_id(client: AsyncClient, headers: dict) -> str:
    response = await client.get("/api/v1/auth/me", headers=headers)
    return response.json()["id"]


async def test_public_monetization_config_has_no_auth_requirement_and_expected_defaults(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/monetization/config")
    assert response.status_code == 200
    body = response.json()
    assert body["ads_enabled"] is True
    # spec §2/§22: App Open architecture is prepared but must default to disabled.
    assert body["app_open_ads_enabled"] is False
    assert body["feed_ad_interval"] == 6


async def test_entitlement_defaults_to_free_tier_with_full_daily_limits(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    response = await client.get("/api/v1/monetization/entitlement", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "FREE"
    assert body["is_pro"] is False
    assert body["should_show_ads"] is True
    assert body["ats_used_today"] == 0
    assert body["ats_daily_limit"] == 3
    assert body["ats_remaining_today"] == 3
    assert body["aptitude_daily_limit"] == 1
    assert body["aptitude_remaining_today"] == 1


async def test_ats_usage_today_reduces_remaining_count(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _user_headers(client)
    user_id = await _current_user_id(client, headers)

    db_session.add(
        AtsAnalysis(
            user_id=user_id,
            overall_score=70,
            score_breakdown={"skills": 70},
            strong_matches=[],
            missing_keywords=[],
            formatting_issues=[],
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/monetization/entitlement", headers=headers)
    body = response.json()
    assert body["ats_used_today"] == 1
    assert body["ats_remaining_today"] == 2


async def test_claiming_reward_widens_daily_limit(client: AsyncClient) -> None:
    headers = await _user_headers(client)
    claim = await client.post(
        "/api/v1/monetization/rewards/claim",
        headers=headers,
        json={"reward_type": "EXTRA_APTITUDE_TEST", "reference_id": "watch-1"},
    )
    assert claim.status_code == 201
    assert claim.json()["reward_type"] == "EXTRA_APTITUDE_TEST"

    entitlement = await client.get("/api/v1/monetization/entitlement", headers=headers)
    assert entitlement.json()["aptitude_daily_limit"] == 2
    assert entitlement.json()["aptitude_remaining_today"] == 2


async def test_duplicate_reward_reference_id_is_idempotent_not_double_granted(client: AsyncClient) -> None:
    """Spec §17: if the SDK's reward callback fires twice for the same ad watch, exactly one
    reward must be granted, never two."""
    headers = await _user_headers(client)
    first = await client.post(
        "/api/v1/monetization/rewards/claim",
        headers=headers,
        json={"reward_type": "EXTRA_ATS_ANALYSIS", "reference_id": "watch-dup"},
    )
    second = await client.post(
        "/api/v1/monetization/rewards/claim",
        headers=headers,
        json={"reward_type": "EXTRA_ATS_ANALYSIS", "reference_id": "watch-dup"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    entitlement = await client.get("/api/v1/monetization/entitlement", headers=headers)
    # Base limit (3) + exactly one reward (not two) = 4.
    assert entitlement.json()["ats_daily_limit"] == 4


async def test_another_users_reference_id_cannot_be_reused(client: AsyncClient) -> None:
    headers_a = await _user_headers(client, "reward-a@example.com")
    headers_b = await _user_headers(client, "reward-b@example.com")

    first = await client.post(
        "/api/v1/monetization/rewards/claim",
        headers=headers_a,
        json={"reward_type": "EXTRA_APTITUDE_TEST", "reference_id": "shared-ref"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/monetization/rewards/claim",
        headers=headers_b,
        json={"reward_type": "EXTRA_APTITUDE_TEST", "reference_id": "shared-ref"},
    )
    assert second.status_code == 409


async def test_admin_can_edit_monetization_config_and_free_limits(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_admin(db_session, role=AdminRole.SUPER_ADMIN)
    admin_headers = await _admin_headers(client)

    update = await client.put(
        "/api/v1/admin/settings/monetization_config",
        headers=admin_headers,
        json={"value": {
            "ads_enabled": False,
            "banner_ads_enabled": False,
            "interstitial_ads_enabled": False,
            "rewarded_ads_enabled": False,
            "app_open_ads_enabled": False,
            "feed_ad_interval": 6,
            "interstitial_min_interval_seconds": 480,
            "interstitial_max_per_session": 3,
        }},
    )
    assert update.status_code == 200

    public_config = await client.get("/api/v1/monetization/config")
    assert public_config.json()["ads_enabled"] is False


async def test_aptitude_session_creation_is_blocked_past_the_free_daily_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Phase 11 §64 — closes the Phase 10 gap: the backend, not just the mobile UI, is now
    authoritative for the free-tier daily aptitude limit."""
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client, "limit-enforced@example.com")

    first = await client.post(
        "/api/v1/aptitude/sessions",
        headers=headers,
        json={"sections": ["numerical-test"], "difficulty": "EASY", "question_count": 1, "timing": "UNTIMED"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/aptitude/sessions",
        headers=headers,
        json={"sections": ["numerical-test"], "difficulty": "EASY", "question_count": 1, "timing": "UNTIMED"},
    )
    assert second.status_code == 402


async def test_a_claimed_reward_unlocks_exactly_one_extra_aptitude_session_server_side(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client, "reward-unlocks-session@example.com")

    await _create_session(client, headers, sections=["numerical-test"], question_count=1)
    blocked = await client.post(
        "/api/v1/aptitude/sessions",
        headers=headers,
        json={"sections": ["numerical-test"], "difficulty": "EASY", "question_count": 1, "timing": "UNTIMED"},
    )
    assert blocked.status_code == 402

    claim = await client.post(
        "/api/v1/monetization/rewards/claim",
        headers=headers,
        json={"reward_type": "EXTRA_APTITUDE_TEST", "reference_id": "unlock-a-session"},
    )
    assert claim.status_code == 201

    unlocked = await client.post(
        "/api/v1/aptitude/sessions",
        headers=headers,
        json={"sections": ["numerical-test"], "difficulty": "EASY", "question_count": 1, "timing": "UNTIMED"},
    )
    assert unlocked.status_code == 201

    # The reward was consumed by that one extra session — a third attempt is blocked again.
    blocked_again = await client.post(
        "/api/v1/aptitude/sessions",
        headers=headers,
        json={"sections": ["numerical-test"], "difficulty": "EASY", "question_count": 1, "timing": "UNTIMED"},
    )
    assert blocked_again.status_code == 402


async def test_pro_users_are_never_blocked_by_the_free_daily_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_numerical_bank(db_session)
    headers = await _user_headers(client, "pro-unlimited@example.com")
    user_id = await _current_user_id(client, headers)

    from sqlalchemy import select

    from app.models.user import SubscriptionTier, User

    result = await db_session.execute(select(User).where(User.id == user_id))
    result.scalar_one().subscription_tier = SubscriptionTier.PRO
    await db_session.commit()

    for _ in range(3):
        response = await client.post(
            "/api/v1/aptitude/sessions",
            headers=headers,
            json={"sections": ["numerical-test"], "difficulty": "EASY", "question_count": 1, "timing": "UNTIMED"},
        )
        assert response.status_code == 201
