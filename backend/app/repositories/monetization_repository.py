from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monetization import RewardUnlock


def _as_aware_utc(value: datetime) -> datetime:
    # SQLite stores DateTime(timezone=True) values as naive strings, so a value read back needs
    # tzinfo reattached before comparing against an aware `now` — same pattern as
    # app/services/content_lifecycle_service.py and app/services/job_service.py.
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class RewardUnlockRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_reference_id(self, reference_id: str) -> RewardUnlock | None:
        result = await self.db.execute(
            select(RewardUnlock).where(RewardUnlock.reference_id == reference_id)
        )
        return result.scalar_one_or_none()

    async def create(self, reward: RewardUnlock) -> RewardUnlock:
        self.db.add(reward)
        await self.db.flush()
        return reward

    async def list_unused_for_user(self, user_id: str, *, reward_type, now: datetime) -> list[RewardUnlock]:
        result = await self.db.execute(
            select(RewardUnlock).where(
                RewardUnlock.user_id == user_id,
                RewardUnlock.reward_type == reward_type,
                RewardUnlock.used_at.is_(None),
            )
        )
        rows = result.scalars().all()
        return [r for r in rows if r.expires_at is None or _as_aware_utc(r.expires_at) > now]

    async def mark_used(self, reward: RewardUnlock, *, used_at: datetime) -> None:
        """Not called anywhere yet — hard enforcement (actually blocking a new ATS analysis/
        aptitude session once the daily limit + unused rewards are exhausted) isn't wired into
        AtsService/AptitudeService this phase, to avoid a new blocking rule destabilizing their
        existing, heavily-tested behavior. Today an unused reward simply widens the reported
        `*_remaining_today` count until it expires (24h) — see MonetizationService.get_entitlement
        and MONETIZATION.md. This method exists for that future wiring."""
        reward.used_at = used_at
        await self.db.flush()
