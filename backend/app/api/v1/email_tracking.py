from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.email_tracking import EmailProvider
from app.models.user import User
from app.schemas.email_tracking import (
    AssignApplicationIn,
    ConnectStartOut,
    EmailConnectionOut,
    ProviderAvailabilityOut,
    RecruitmentEmailEventOut,
)
from app.security.dependencies import get_current_user
from app.services.email_tracking_service import PREP_HINT_BY_STAGE, EmailTrackingService

router = APIRouter()


@router.get("/providers", response_model=ProviderAvailabilityOut)
async def get_provider_availability(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ProviderAvailabilityOut:
    return await EmailTrackingService(db).get_availability(user.id)


@router.get("/connections", response_model=list[EmailConnectionOut])
async def list_connections(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[EmailConnectionOut]:
    connections = await EmailTrackingService(db).list_connections(user.id)
    return [EmailConnectionOut.model_validate(c) for c in connections]


@router.post("/gmail/connect", response_model=ConnectStartOut)
async def connect_gmail(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> ConnectStartOut:
    return await EmailTrackingService(db).start_connect(user.id, EmailProvider.GMAIL)


@router.post("/outlook/connect", response_model=ConnectStartOut)
async def connect_outlook(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> ConnectStartOut:
    return await EmailTrackingService(db).start_connect(user.id, EmailProvider.OUTLOOK)


@router.get("/gmail/callback")
async def gmail_callback(code: str, state: str, db: AsyncSession = Depends(get_db)) -> dict:
    await EmailTrackingService(db).handle_oauth_callback(EmailProvider.GMAIL, code=code, state=state)
    return {"detail": "Gmail connected. Return to the CareerOS app to continue."}


@router.get("/outlook/callback")
async def outlook_callback(code: str, state: str, db: AsyncSession = Depends(get_db)) -> dict:
    await EmailTrackingService(db).handle_oauth_callback(EmailProvider.OUTLOOK, code=code, state=state)
    return {"detail": "Outlook connected. Return to the CareerOS app to continue."}


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    connection_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    await EmailTrackingService(db).disconnect(user.id, connection_id)


@router.delete("/data", status_code=status.HTTP_200_OK)
async def delete_tracking_data(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    deleted = await EmailTrackingService(db).delete_tracking_data(user.id)
    return {"deleted_events": deleted}


@router.get("/events", response_model=list[RecruitmentEmailEventOut])
async def list_events(
    application_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RecruitmentEmailEventOut]:
    events = await EmailTrackingService(db).list_events(user.id, application_id=application_id)
    return [RecruitmentEmailEventOut.model_validate(e) for e in events]


@router.get("/events/{event_id}", response_model=RecruitmentEmailEventOut)
async def get_event(
    event_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> RecruitmentEmailEventOut:
    event = await EmailTrackingService(db).get_event(user.id, event_id)
    return RecruitmentEmailEventOut.model_validate(event)


@router.post("/events/{event_id}/confirm", response_model=RecruitmentEmailEventOut)
async def confirm_event(
    event_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> RecruitmentEmailEventOut:
    event = await EmailTrackingService(db).confirm_event(user.id, event_id)
    out = RecruitmentEmailEventOut.model_validate(event)
    return out


@router.get("/events/{event_id}/prep-hint")
async def get_prep_hint(
    event_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    """Spec §30/§62 — after confirming, the mobile client asks this to decide whether to offer
    "Prepare for Aptitude Test" (Phase 6) or "Prepare for Interview" (Phase 7), reusing those
    existing flows rather than building a duplicate one."""
    event = await EmailTrackingService(db).get_event(user.id, event_id)
    stage = event.detected_stage
    hint = PREP_HINT_BY_STAGE.get(stage) if stage else None
    return {"prep_flow": hint}


@router.post("/events/{event_id}/ignore", response_model=RecruitmentEmailEventOut)
async def ignore_event(
    event_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> RecruitmentEmailEventOut:
    event = await EmailTrackingService(db).ignore_event(user.id, event_id)
    return RecruitmentEmailEventOut.model_validate(event)


@router.post("/events/{event_id}/assign-application", response_model=RecruitmentEmailEventOut)
async def assign_application(
    event_id: str,
    payload: AssignApplicationIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecruitmentEmailEventOut:
    event = await EmailTrackingService(db).assign_application(user.id, event_id, payload.application_id)
    return RecruitmentEmailEventOut.model_validate(event)
