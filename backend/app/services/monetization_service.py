"""Phase 10 — entitlements, free-tier usage, and the rewarded-ad ledger.

Time-zone policy (spec §54): "today" is always the current **UTC calendar day**
(`datetime.now(timezone.utc)` truncated to midnight). CareerOS does not currently store a user's
local timezone, so UTC is the only value that's actually correct everywhere — this also means no
reset job is ever needed: usage-today is a date-window query against existing tables
(`AtsAnalysis`/`TestSession`), never a physically-reset counter (spec §54's explicit instruction).
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ats_analysis import AtsAnalysis
from app.models.monetization import RewardType, RewardUnlock
from app.models.test_session import TestSession
from app.models.user import SubscriptionTier, User
from app.repositories.monetization_repository import RewardUnlockRepository
from app.services import system_settings_service


def _utc_day_start(now: datetime) -> datetime:
    return now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _as_aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class MonetizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.rewards = RewardUnlockRepository(db)

    async def get_public_config(self) -> dict:
        """Non-secret ad/frequency configuration a client fetches at startup (spec §6/§39). Never
        contains AdMob credentials — those live in mobile build config, never here."""
        return await system_settings_service.get_monetization_config(self.db)

    async def _count_today(self, model, user_id: str, now: datetime) -> int:
        day_start = _utc_day_start(now)
        result = await self.db.execute(
            select(func.count()).select_from(model).where(model.user_id == user_id, model.created_at >= day_start)
        )
        return result.scalar_one()

    async def get_entitlement(self, user: User) -> dict:
        now = datetime.now(timezone.utc)
        is_pro = user.subscription_tier == SubscriptionTier.PRO and (
            user.entitlement_expires_at is None or _as_aware_utc(user.entitlement_expires_at) > now
        )
        limits = await system_settings_service.get_free_tier_limits(self.db)

        ats_used = await self._count_today(AtsAnalysis, user.id, now)
        aptitude_used = await self._count_today(TestSession, user.id, now)

        extra_ats = len(await self.rewards.list_unused_for_user(user.id, reward_type=RewardType.EXTRA_ATS_ANALYSIS, now=now))
        extra_aptitude = len(
            await self.rewards.list_unused_for_user(user.id, reward_type=RewardType.EXTRA_APTITUDE_TEST, now=now)
        )

        ats_limit = limits["ats_daily"] + extra_ats
        aptitude_limit = limits["aptitude_daily"] + extra_aptitude

        return {
            "tier": user.subscription_tier.value,
            "is_pro": is_pro,
            "should_show_ads": not is_pro,
            "can_use_unlimited_ats": is_pro,
            "can_use_unlimited_aptitude": is_pro,
            "can_use_advanced_analytics": is_pro,
            "ats_used_today": ats_used,
            "ats_daily_limit": None if is_pro else ats_limit,
            "ats_remaining_today": None if is_pro else max(ats_limit - ats_used, 0),
            "aptitude_used_today": aptitude_used,
            "aptitude_daily_limit": None if is_pro else aptitude_limit,
            "aptitude_remaining_today": None if is_pro else max(aptitude_limit - aptitude_used, 0),
        }

    async def claim_reward(
        self, user_id: str, *, reward_type: RewardType, reference_id: str, source: str = "rewarded_ad"
    ) -> RewardUnlock:
        """Idempotent on `reference_id` (spec §17): a duplicate claim for the same ad-watch
        returns the existing reward unchanged rather than granting a second one. The caller
        (mobile `AdService`) must only call this from the SDK's actual earned-reward callback —
        never merely because an ad loaded, started, or was dismissed (spec §15)."""
        existing = await self.rewards.get_by_reference_id(reference_id)
        if existing is not None:
            if existing.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reward reference already claimed.")
            return existing

        now = datetime.now(timezone.utc)
        reward = RewardUnlock(
            user_id=user_id,
            reward_type=reward_type,
            granted_at=now,
            expires_at=now + timedelta(hours=24),
            source=source,
            reference_id=reference_id,
        )
        await self.rewards.create(reward)
        await self.db.commit()
        return reward
