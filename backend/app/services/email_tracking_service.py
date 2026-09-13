"""Orchestrates Phase 8 end to end. This module is the one place that is allowed to call
`ApplicationService.update_stage` on behalf of a recruitment-email suggestion — see `confirm_event`
— and it only ever does so after `POST /email-tracking/events/{id}/confirm` has been explicitly
called by the user. Nothing in the webhook/processing path below ever touches `current_stage`.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.email_tracking.classifier import classify_stage
from app.email_tracking.confidence import compute_confidence
from app.email_tracking.matcher import match_application
from app.email_tracking.matching_config import SUGGEST_MIN_CONFIDENCE
from app.email_tracking.text_utils import as_aware_utc
import re
from app.email_tracking.types import ApplicationSignal, RawEmail
from app.models.application import ApplicationStage
from app.models.email_tracking import (
    EmailConnection,
    EmailConnectionStatus,
    EmailForwardingAlias,
    EmailProvider,
    OAuthState,
    RecruitmentEmailEvent,
    RecruitmentEventStatus,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.email_tracking_repository import (
    EmailConnectionRepository,
    EmailForwardingAliasRepository,
    OAuthStateRepository,
    RecruitmentEmailEventRepository,
)
from app.schemas.application import ApplicationStageUpdate
from app.schemas.email_tracking import ConnectStartOut, ProviderAvailabilityOut
from app.services.application_service import ApplicationService
from app.services.email_tracking_providers import (
    EmailTrackingProvider,
    GmailTrackingProvider,
    MockEmailTrackingProvider,
    OutlookTrackingProvider,
    StaleSyncCursorError,
)
from app.services.token_encryption_service import TokenDecryptionError, TokenEncryptionService

_OAUTH_STATE_TTL = timedelta(minutes=15)
_EVIDENCE_EXCERPT_MAX_LEN = 240

# Preparation-flow stages (spec §30/§62) — surfaced to the mobile client via
# `RecruitmentEmailEventOut`/confirm response so it can offer "Prepare for Aptitude Test"/
# "Prepare for Interview" without CareerOS inventing a second preparation flow.
PREP_HINT_BY_STAGE = {
    ApplicationStage.APTITUDE_TEST: "aptitude",
    ApplicationStage.INTERVIEW: "interview",
    ApplicationStage.FINAL_INTERVIEW: "interview",
    ApplicationStage.ASSESSMENT_CENTRE: "interview",
}


class EmailTrackingService:
    def __init__(self, db: AsyncSession, *, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.connections = EmailConnectionRepository(db)
        self.events = RecruitmentEmailEventRepository(db)
        self.oauth_states = OAuthStateRepository(db)
        self.aliases = EmailForwardingAliasRepository(db)
        self.applications = ApplicationRepository(db)
        self.encryption = TokenEncryptionService()

    # ------------------------------------------------------------------
    # Provider selection (spec §39: mock fallback when real credentials are absent)
    # ------------------------------------------------------------------

    def get_provider(self, provider: EmailProvider) -> EmailTrackingProvider:
        if provider == EmailProvider.GMAIL:
            return GmailTrackingProvider(self.settings) if self.settings.gmail_tracking_available else MockEmailTrackingProvider()
        if provider == EmailProvider.OUTLOOK:
            return (
                OutlookTrackingProvider(self.settings) if self.settings.outlook_tracking_available else MockEmailTrackingProvider()
            )
        raise ValueError(f"No live provider for {provider}")

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    async def get_availability(self, user_id: str) -> ProviderAvailabilityOut:
        alias = await self._ensure_alias(user_id) if self.settings.forward_email_available else None
        return ProviderAvailabilityOut(
            gmail_available=self.settings.gmail_tracking_available,
            outlook_available=self.settings.outlook_tracking_available,
            forward_email_available=self.settings.forward_email_available,
            forward_email_alias=(f"apply+{alias.alias_token}@{self.settings.forward_email_domain}" if alias else None),
        )

    async def _ensure_alias(self, user_id: str) -> EmailForwardingAlias:
        existing = await self.aliases.get_for_user(user_id)
        if existing:
            return existing
        alias = self.aliases.add(
            EmailForwardingAlias(user_id=user_id, alias_token=secrets.token_urlsafe(24))
        )
        await self.db.commit()
        await self.db.refresh(alias)
        return alias

    async def list_connections(self, user_id: str) -> list[EmailConnection]:
        return await self.connections.list_for_user(user_id)

    async def start_connect(self, user_id: str, provider: EmailProvider) -> ConnectStartOut:
        available = {
            EmailProvider.GMAIL: self.settings.gmail_tracking_available,
            EmailProvider.OUTLOOK: self.settings.outlook_tracking_available,
        }.get(provider, False)
        if not available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{provider.value.title()} tracking is not available in this environment yet.",
            )
        state_value = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        self.oauth_states.add(
            OAuthState(state=state_value, user_id=user_id, provider=provider, created_at=now, expires_at=now + _OAUTH_STATE_TTL)
        )
        await self.db.commit()
        url = self.get_provider(provider).build_authorization_url(state=state_value)
        return ConnectStartOut(authorization_url=url)

    async def handle_oauth_callback(self, provider: EmailProvider, *, code: str, state: str) -> str:
        """Returns the CareerOS user_id the callback belongs to, after validating and permanently
        consuming the OAuth state (spec §44 — never accept a reused or expired state)."""
        state_row = await self.oauth_states.get(state)
        now = datetime.now(timezone.utc)
        if (
            state_row is None
            or state_row.provider != provider
            or state_row.consumed_at is not None
            or as_aware_utc(state_row.expires_at) < now
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state.")
        await self.oauth_states.mark_consumed(state_row, when=now)
        user_id = state_row.user_id

        tokens = await self.get_provider(provider).exchange_code(code=code)
        existing = await self.connections.get_active_by_provider(user_id, provider)
        if existing:
            existing.encrypted_access_token = self.encryption.encrypt(tokens.access_token)
            if tokens.refresh_token:
                existing.encrypted_refresh_token = self.encryption.encrypt(tokens.refresh_token)
            existing.token_expires_at = tokens.expires_at
            existing.granted_scopes = tokens.scopes
            existing.provider_email = tokens.provider_email or existing.provider_email
            existing.status = EmailConnectionStatus.ACTIVE
            existing.last_error_at = None
            existing.last_error_code = None
            connection = existing
        else:
            connection = self.connections.add(
                EmailConnection(
                    user_id=user_id,
                    provider=provider,
                    provider_account_id=tokens.provider_account_id or secrets.token_hex(16),
                    provider_email=tokens.provider_email,
                    encrypted_access_token=self.encryption.encrypt(tokens.access_token),
                    encrypted_refresh_token=self.encryption.encrypt(tokens.refresh_token) if tokens.refresh_token else None,
                    token_expires_at=tokens.expires_at,
                    granted_scopes=tokens.scopes,
                    status=EmailConnectionStatus.ACTIVE,
                )
            )
        await self.db.flush()

        watch = await self.get_provider(provider).establish_watch(access_token=tokens.access_token)
        if provider == EmailProvider.GMAIL:
            connection.gmail_history_id = watch.cursor
            connection.gmail_watch_expiry = watch.expires_at
        else:
            connection.outlook_subscription_id = watch.external_id
            connection.outlook_subscription_expiry = watch.expires_at
        connection.last_sync_at = datetime.now(timezone.utc)
        await self.db.commit()
        return user_id

    async def disconnect(self, user_id: str, connection_id: str) -> None:
        connection = await self.connections.get_owned(connection_id, user_id)
        if connection is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
        try:
            access_token = self._decrypt_or_none(connection.encrypted_access_token)
            refresh_token = self._decrypt_or_none(connection.encrypted_refresh_token)
            if access_token:
                await self.get_provider(connection.provider).revoke(access_token=access_token, refresh_token=refresh_token)
        except Exception:
            # Best-effort revoke (spec §34 "where supported") — a provider outage must not block
            # the user from disconnecting on the CareerOS side.
            pass
        connection.status = EmailConnectionStatus.DISCONNECTED
        connection.disconnected_at = datetime.now(timezone.utc)
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = None
        await self.db.commit()

    async def delete_tracking_data(self, user_id: str) -> int:
        """Spec §35 — deletes stored recruitment-email metadata/suggestions only. Confirmed
        `ApplicationStageEvent` rows are untouched; they live on the `applications` aggregate, not
        here, and this method never reaches into that table."""
        events = await self.events.list_for_user(user_id)
        for event in events:
            await self.db.delete(event)
        await self.db.commit()
        return len(events)

    def _decrypt_or_none(self, ciphertext: str | None) -> str | None:
        if not ciphertext:
            return None
        try:
            return self.encryption.decrypt(ciphertext)
        except TokenDecryptionError:
            return None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    async def list_events(self, user_id: str, *, application_id: str | None = None) -> list[RecruitmentEmailEvent]:
        return await self.events.list_for_user(user_id, application_id=application_id)

    async def count_needing_review(self, user_id: str) -> int:
        return await self.events.count_needing_review(user_id)

    async def get_event(self, user_id: str, event_id: str) -> RecruitmentEmailEvent:
        event = await self.events.get_owned(event_id, user_id)
        if event is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recruitment event not found")
        return event

    async def ignore_event(self, user_id: str, event_id: str) -> RecruitmentEmailEvent:
        event = await self.get_event(user_id, event_id)
        if event.status in (RecruitmentEventStatus.CONFIRMED, RecruitmentEventStatus.IGNORED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This update has already been reviewed.")
        event.status = RecruitmentEventStatus.IGNORED
        event.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return event

    async def assign_application(self, user_id: str, event_id: str, application_id: str) -> RecruitmentEmailEvent:
        """Spec §25/§67 — resolves an AMBIGUOUS event once the user tells CareerOS which of the
        candidate applications it actually belongs to. Never accepts an application outside the
        candidate list (or outside this user's own applications) — no guessing, ever."""
        event = await self.get_event(user_id, event_id)
        if event.status != RecruitmentEventStatus.AMBIGUOUS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This update is not awaiting an application choice.")
        if application_id not in event.candidate_application_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Not one of the candidate applications for this update.")
        application = await self.applications.get_owned(application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        event.matched_application_id = application_id
        event.candidate_application_ids = []
        event.status = RecruitmentEventStatus.SUGGESTED if event.detected_stage else RecruitmentEventStatus.UNMATCHED
        await self.db.commit()
        return event

    async def confirm_event(self, user_id: str, event_id: str) -> RecruitmentEmailEvent:
        """The one and only path from a recruitment-email suggestion to a real stage change (spec
        §28/§41). Every precondition is checked before anything is written; the stage transition
        and the event's CONFIRMED flag are then written in one transaction (see
        `ApplicationService.update_stage`'s `commit=False`)."""
        event = await self.get_event(user_id, event_id)
        if event.status == RecruitmentEventStatus.CONFIRMED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This update has already been confirmed.")
        if event.status == RecruitmentEventStatus.IGNORED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This update was already dismissed.")
        if event.matched_application_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No application is matched yet — assign one first.")
        if event.detected_stage is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No stage was detected for this update.")

        application = await self.applications.get_owned(event.matched_application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matched application not found")

        stage = ApplicationStage(event.detected_stage)
        await ApplicationService(self.db).update_stage(
            user_id,
            application.id,
            ApplicationStageUpdate(stage=stage, note=f"Confirmed from a recruitment email ({event.sender_domain})"),
            source="EMAIL_CONFIRMED",
            commit=False,
        )
        event.status = RecruitmentEventStatus.CONFIRMED
        event.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    # ------------------------------------------------------------------
    # Processing pipeline (spec §14/§19-27) — never touches current_stage.
    # ------------------------------------------------------------------

    async def process_message(self, user_id: str, connection: EmailConnection | None, email: RawEmail) -> RecruitmentEmailEvent | None:
        """Runs one message through pre-filter → classify → match → persist. Returns None (no row
        created) when the message doesn't even pass the recruitment pre-filter — CareerOS is not a
        shadow mailbox (spec §18) and irrelevant mail leaves no trace at all."""
        sender_domain = email.sender_email.rsplit("@", 1)[-1].lower() if "@" in email.sender_email else ""
        stage_result = classify_stage(subject=email.subject, body_text=email.body_text, sender_domain=sender_domain)
        if not stage_result.is_recruitment_related:
            return None

        provider = connection.provider if connection else EmailProvider.FORWARDED
        applications = await self.applications.list_all_for_user(user_id)
        signals = [
            ApplicationSignal(
                application_id=a.id,
                company_name=a.company_name,
                role_title=a.role_title,
                job_url=a.job_url,
                location=a.location,
                applied_date=a.applied_date,
            )
            for a in applications
        ]
        match = match_application(email, sender_domain, signals)

        confidence_score, confidence_label = (0.0, "LOW")
        if stage_result.stage:
            confidence_score, confidence_label = compute_confidence(stage_result, match.signals)

        if match.status == "matched" and stage_result.stage and confidence_score >= SUGGEST_MIN_CONFIDENCE:
            event_status = RecruitmentEventStatus.SUGGESTED
        elif match.status == "ambiguous" and stage_result.stage:
            event_status = RecruitmentEventStatus.AMBIGUOUS
        elif match.status == "matched" and stage_result.stage:
            # Matched an application but confidence is too low to bother the user — still worth
            # recording as reviewable-if-curious, never pushed (spec §26).
            event_status = RecruitmentEventStatus.DETECTED
        else:
            event_status = RecruitmentEventStatus.UNMATCHED

        event = RecruitmentEmailEvent(
            user_id=user_id,
            email_connection_id=connection.id if connection else None,
            provider=provider,
            provider_message_id=email.provider_message_id,
            provider_thread_id=email.provider_thread_id,
            sender_email=email.sender_email,
            sender_domain=sender_domain,
            sender_name=email.sender_name,
            subject=email.subject[:500],
            evidence_excerpt=_build_excerpt(stage_result.evidence),
            received_at=email.received_at,
            matched_application_id=match.matched_id,
            candidate_application_ids=match.candidate_ids,
            detected_stage=stage_result.stage,
            confidence_score=confidence_score if stage_result.stage else None,
            confidence_label=confidence_label if stage_result.stage else None,
            classification_reason_json={"evidence": stage_result.evidence + match.evidence},
            status=event_status,
        )
        created = await self.events.try_add(event)
        if created is None:
            return None  # spec §9/§42 — duplicate delivery of the same provider message is a no-op.
        await self.db.commit()
        await self.db.refresh(created)
        return created

    # ------------------------------------------------------------------
    # Watch/subscription renewal (spec §58-59) — called by a scheduled job, not a request handler.
    # ------------------------------------------------------------------

    async def renew_expiring_watches(self, *, within: timedelta = timedelta(hours=24)) -> int:
        deadline = datetime.now(timezone.utc) + within
        renewed = 0
        for connection in await self.connections.list_all_active(EmailProvider.GMAIL):
            if connection.gmail_watch_expiry and as_aware_utc(connection.gmail_watch_expiry) > deadline:
                continue
            await self._renew_one(connection)
            renewed += 1
        for connection in await self.connections.list_all_active(EmailProvider.OUTLOOK):
            if connection.outlook_subscription_expiry and as_aware_utc(connection.outlook_subscription_expiry) > deadline:
                continue
            await self._renew_one(connection)
            renewed += 1
        return renewed

    async def resubscribe(self, connection: EmailConnection) -> None:
        """Public entry point for spec §12's "on subscriptionRemoved, attempt safe recreation" —
        thin wrapper so the webhook layer doesn't need to reach into a private method."""
        await self._renew_one(connection)

    async def _renew_one(self, connection: EmailConnection) -> None:
        access_token = self._decrypt_or_none(connection.encrypted_access_token)
        if access_token is None:
            connection.status = EmailConnectionStatus.REAUTHORIZATION_REQUIRED
            await self.db.commit()
            return
        provider = self.get_provider(connection.provider)
        try:
            current_cursor = connection.gmail_history_id or connection.outlook_subscription_id or ""
            watch = await provider.renew_watch(access_token=access_token, current_cursor=current_cursor)
            if connection.provider == EmailProvider.GMAIL:
                connection.gmail_history_id = watch.cursor
                connection.gmail_watch_expiry = watch.expires_at
            else:
                connection.outlook_subscription_id = watch.external_id
                connection.outlook_subscription_expiry = watch.expires_at
            connection.status = EmailConnectionStatus.ACTIVE
            connection.last_error_at = None
            connection.last_error_code = None
        except Exception as exc:  # noqa: BLE001 — provider errors are classified, not re-raised.
            connection.status = EmailConnectionStatus.ERROR
            connection.last_error_at = datetime.now(timezone.utc)
            connection.last_error_code = type(exc).__name__
        await self.db.commit()

    # ------------------------------------------------------------------
    # Sync (spec §7/§12 — reconciliation when notifications were missed/expired/duplicated)
    # ------------------------------------------------------------------

    async def sync_connection(self, connection: EmailConnection) -> list[RecruitmentEmailEvent]:
        access_token = self._decrypt_or_none(connection.encrypted_access_token)
        if access_token is None:
            connection.status = EmailConnectionStatus.REAUTHORIZATION_REQUIRED
            await self.db.commit()
            return []
        provider = self.get_provider(connection.provider)
        cursor = connection.gmail_history_id or ""
        try:
            message_ids, new_cursor = await provider.list_changed_message_ids(access_token=access_token, cursor=cursor)
        except StaleSyncCursorError:
            watch = await provider.establish_watch(access_token=access_token)
            connection.gmail_history_id = watch.cursor
            connection.gmail_watch_expiry = watch.expires_at
            await self.db.commit()
            return []

        created_events: list[RecruitmentEmailEvent] = []
        for message_id in message_ids:
            email = await provider.fetch_message(access_token=access_token, message_id=message_id)
            created = await self.process_message(connection.user_id, connection, email)
            if created:
                created_events.append(created)

        if connection.provider == EmailProvider.GMAIL:
            connection.gmail_history_id = new_cursor
        connection.last_sync_at = datetime.now(timezone.utc)
        await self.db.commit()
        return created_events


def _build_excerpt(evidence: list[str]) -> str | None:
    if not evidence:
        return None
    excerpt = re.sub(r"\s+", " ", " · ".join(evidence)).strip()
    return excerpt[:_EVIDENCE_EXCERPT_MAX_LEN] or None
