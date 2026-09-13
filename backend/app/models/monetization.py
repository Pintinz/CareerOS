import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class RewardType(str, enum.Enum):
    EXTRA_APTITUDE_TEST = "EXTRA_APTITUDE_TEST"
    EXTRA_ATS_ANALYSIS = "EXTRA_ATS_ANALYSIS"
    PREMIUM_PRACTICE_SET = "PREMIUM_PRACTICE_SET"
    ADVANCED_REPORT = "ADVANCED_REPORT"


class RewardUnlock(TimestampMixin, Base):
    """A persisted grant from a completed rewarded ad (spec §16-17) — never inferred from Flutter
    widget state alone. `reference_id` is a client-generated idempotency key (one per ad-watch
    attempt); the unique constraint on it means a duplicated reward callback (network retry, the
    SDK firing twice) can create at most one row — see `MonetizationService.claim_reward`.

    No AdMob server-side verification (SSV) exists in this environment — this is the documented
    "mock verifier" spec §55 explicitly allows for development; a real deployment should add SSV
    before trusting this endpoint against real ad revenue. See MONETIZATION.md."""

    __tablename__ = "reward_unlocks"
    __table_args__ = (UniqueConstraint("reference_id", name="uq_reward_unlocks_reference_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reward_type: Mapped[RewardType] = mapped_column(Enum(RewardType), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="rewarded_ad")
    reference_id: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
