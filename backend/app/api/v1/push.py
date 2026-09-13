from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.push import DeviceTokenRegister, NotificationPreferencesOut, NotificationPreferencesUpdate
from app.security.dependencies import get_current_user
from app.services.push_service import PushService

router = APIRouter()


@router.post("/devices", status_code=status.HTTP_204_NO_CONTENT)
async def register_device(
    payload: DeviceTokenRegister, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await PushService(db).register_token(user.id, platform=payload.platform, token=payload.token)


@router.delete("/devices/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(
    token: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await PushService(db).unregister_token(user.id, token)


@router.get("/preferences", response_model=NotificationPreferencesOut)
async def get_preferences(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> NotificationPreferencesOut:
    prefs = await PushService(db).get_preferences(user.id)
    return NotificationPreferencesOut.model_validate(prefs)


@router.put("/preferences", response_model=NotificationPreferencesOut)
async def update_preferences(
    payload: NotificationPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationPreferencesOut:
    prefs = await PushService(db).update_preferences(user.id, **payload.model_dump())
    return NotificationPreferencesOut.model_validate(prefs)
