"""Provider webhook endpoints (spec §8/§13/§40). Every handler here follows spec §13's rule:
validate → acknowledge quickly → do the actual work. None of them perform classification before
returning a response to the provider — they go through `BackgroundTaskRunner.enqueue`, which in
this codebase's current (no-Celery-yet) configuration still runs inline, but through the same
interface a real queue would use, so swapping it later touches one file, not these routes.

None of these payloads are trusted as-is (spec §9 "a notification means the mailbox changed, NOT
this is definitely a recruitment email", and spec §43 "protect against forged webhooks"). Gmail's
Pub/Sub push messages carry no application-level signature by default; the practical verification
this endpoint performs is: only the connection matching the notified mailbox is ever touched, and
that connection's own stored `gmail_history_id` is what bounds what gets fetched — an attacker
sending a forged notification for an arbitrary email address can, at worst, trigger a wasted sync
call for that address if it's an existing CareerOS connection; they can never target another user's
mailbox from this alone (the actual message fetch still requires that user's own stored, encrypted
OAuth token). Production deployments should additionally verify the Pub/Sub JWT per Google's
documented method — see DEPLOYMENT.md.
"""

import base64
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.email_tracking import EmailConnectionStatus, EmailProvider
from app.repositories.email_tracking_repository import EmailConnectionRepository
from app.schemas.email_tracking import GmailWebhookIn
from app.services.background_tasks import InlineTaskRunner
from app.services.email_tracking_service import EmailTrackingService

router = APIRouter()
_runner = InlineTaskRunner()


@router.post("/gmail", status_code=status.HTTP_204_NO_CONTENT)
async def gmail_webhook(payload: GmailWebhookIn, db: AsyncSession = Depends(get_db)) -> None:
    settings = get_settings()
    if settings.google_pubsub_topic and payload.subscription and settings.google_pubsub_topic not in payload.subscription:
        # Expected-topic validation (spec §8) — a push message claiming to come from a Pub/Sub
        # subscription that doesn't reference our configured topic is rejected outright.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unexpected Pub/Sub subscription.")

    notification = _decode_gmail_pubsub_message(payload.message.get("data", ""))
    email_address = notification.get("emailAddress")
    if not email_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Gmail notification.")

    active_connections = await EmailConnectionRepository(db).list_all_active(EmailProvider.GMAIL)
    match = next((c for c in active_connections if c.provider_email == email_address), None)
    if match is None or match.status != EmailConnectionStatus.ACTIVE:
        # Not a forged-webhook signal by itself (spec §9: could just be a stale/disconnected
        # account) — quietly acknowledged, nothing to sync.
        return None

    async def _process() -> None:
        await EmailTrackingService(db).sync_connection(match)

    await _runner.enqueue("gmail_sync", _process)
    return None


@router.post("/microsoft", status_code=status.HTTP_202_ACCEPTED)
async def microsoft_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict | str:
    # Graph subscription-creation validation handshake (spec §13): Microsoft calls this same URL
    # with a `validationToken` query parameter and expects it echoed back as plain text.
    validation_token = request.query_params.get("validationToken")
    if validation_token is not None:
        return PlainTextResponse(validation_token, status_code=status.HTTP_200_OK)

    body = await request.json()
    notifications = body.get("value", [])
    connections_repo = EmailConnectionRepository(db)

    async def _process(subscription_id: str) -> None:
        active = await connections_repo.list_all_active(EmailProvider.OUTLOOK)
        match = next((c for c in active if c.outlook_subscription_id == subscription_id), None)
        if match and match.status == EmailConnectionStatus.ACTIVE:
            await EmailTrackingService(db).sync_connection(match)

    for notification in notifications:
        subscription_id = notification.get("subscriptionId")
        if not subscription_id:
            continue
        await _runner.enqueue("outlook_sync", lambda sid=subscription_id: _process(sid))
    return {"status": "accepted"}


@router.post("/microsoft/lifecycle", status_code=status.HTTP_202_ACCEPTED)
async def microsoft_lifecycle_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict | str:
    validation_token = request.query_params.get("validationToken")
    if validation_token is not None:
        return PlainTextResponse(validation_token, status_code=status.HTTP_200_OK)

    body = await request.json()
    connections_repo = EmailConnectionRepository(db)
    for notification in body.get("value", []):
        subscription_id = notification.get("subscriptionId")
        lifecycle_event = notification.get("lifecycleEvent")
        if not subscription_id:
            continue
        active = await connections_repo.list_all_active(EmailProvider.OUTLOOK)
        match = next((c for c in active if c.outlook_subscription_id == subscription_id), None)
        if match is None:
            continue
        if lifecycle_event in ("reauthorizationRequired",):
            match.status = EmailConnectionStatus.REAUTHORIZATION_REQUIRED
            await db.commit()
        elif lifecycle_event == "subscriptionRemoved":
            # Spec §12 — attempt safe recreation rather than silently dropping tracking forever.
            async def _recreate(connection=match) -> None:
                await EmailTrackingService(db).resubscribe(connection)

            await _runner.enqueue("outlook_resubscribe", _recreate)
        elif lifecycle_event == "missed":
            async def _reconcile(connection=match) -> None:
                await EmailTrackingService(db).sync_connection(connection)

            await _runner.enqueue("outlook_reconcile", _reconcile)
    return {"status": "accepted"}


def _decode_gmail_pubsub_message(data_b64: str) -> dict:
    if not data_b64:
        return {}
    padded = data_b64 + "=" * (-len(data_b64) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Pub/Sub payload.")
