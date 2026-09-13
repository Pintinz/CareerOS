from datetime import datetime

from pydantic import BaseModel

from app.models.monetization import RewardType


class MonetizationConfigOut(BaseModel):
    ads_enabled: bool
    banner_ads_enabled: bool
    interstitial_ads_enabled: bool
    rewarded_ads_enabled: bool
    app_open_ads_enabled: bool
    feed_ad_interval: int
    interstitial_min_interval_seconds: int
    interstitial_max_per_session: int


class EntitlementOut(BaseModel):
    tier: str
    is_pro: bool
    should_show_ads: bool
    can_use_unlimited_ats: bool
    can_use_unlimited_aptitude: bool
    can_use_advanced_analytics: bool
    ats_used_today: int
    ats_daily_limit: int | None
    ats_remaining_today: int | None
    aptitude_used_today: int
    aptitude_daily_limit: int | None
    aptitude_remaining_today: int | None


class RewardClaimIn(BaseModel):
    reward_type: RewardType
    reference_id: str
    source: str = "rewarded_ad"


class RewardUnlockOut(BaseModel):
    id: str
    reward_type: RewardType
    granted_at: datetime
    expires_at: datetime | None
    source: str
    reference_id: str
    used_at: datetime | None

    model_config = {"from_attributes": True}
