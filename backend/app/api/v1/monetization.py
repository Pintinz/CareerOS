from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.monetization import EntitlementOut, MonetizationConfigOut, RewardClaimIn, RewardUnlockOut
from app.security.dependencies import get_current_user
from app.services.monetization_service import MonetizationService

router = APIRouter()


@router.get("/config", response_model=MonetizationConfigOut)
async def get_monetization_config(db: AsyncSession = Depends(get_db)) -> MonetizationConfigOut:
    """Public, non-secret ad/frequency configuration (spec §6/§39) — no auth required since it
    carries no user- or account-specific data, only global admin-configured toggles. Never
    contains AdMob credentials."""
    config = await MonetizationService(db).get_public_config()
    return MonetizationConfigOut.model_validate(config)


@router.get("/entitlement", response_model=EntitlementOut)
async def get_entitlement(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> EntitlementOut:
    entitlement = await MonetizationService(db).get_entitlement(user)
    return EntitlementOut.model_validate(entitlement)


@router.post("/rewards/claim", response_model=RewardUnlockOut, status_code=201)
async def claim_reward(
    payload: RewardClaimIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> RewardUnlockOut:
    """Grants a reward only once per `reference_id` (spec §17) — the mobile client must generate
    this id once per ad-watch attempt and call this endpoint only from the SDK's actual
    earned-reward callback, never merely because an ad loaded/started/was dismissed (spec §15)."""
    reward = await MonetizationService(db).claim_reward(
        user.id, reward_type=payload.reward_type, reference_id=payload.reference_id, source=payload.source
    )
    return RewardUnlockOut.model_validate(reward)
