"""Phase 8 — Smart Recruitment Email Tracking data models (spec §15/§17/§36).

Nothing here can mutate `Application.current_stage` directly — see
`app/services/email_tracking_service.py::confirm_event`, which is the *only* code path that calls
into `ApplicationService.update_stage` on behalf of a recruitment-email suggestion, and only after
an explicit user confirmation. That is the whole point of this phase's data model: it stores
*suggestions*, never applies them.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class EmailProvider(str, enum.Enum):
    GMAIL = "GMAIL"
    OUTLOOK = "OUTLOOK"
    FORWARDED = "FORWARDED"  # spec §36 — no live connection, arrives via the forwarding alias.


class EmailConnectionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REAUTHORIZATION_REQUIRED = "REAUTHORIZATION_REQUIRED"
    ERROR = "ERROR"
    DISCONNECTED = "DISCONNECTED"


class RecruitmentEventStatus(str, enum.Enum):
    DETECTED = "DETECTED"  # a mailbox change was observed; not yet classified.
    SUGGESTED = "SUGGESTED"  # classified, matched to exactly one application, awaiting confirmation.
    AMBIGUOUS = "AMBIGUOUS"  # classified but matched more than one plausible application.
    UNMATCHED = "UNMATCHED"  # classified but no application evidence matched anything at all.
    CONFIRMED = "CONFIRMED"  # user confirmed — the linked ApplicationStageEvent now exists.
    IGNORED = "IGNORED"  # user dismissed it; no application was changed.


class EmailConnection(TimestampMixin, Base):
    """One user's link to a real mailbox provider. Tokens are Fernet-encrypted at rest
    (`TokenEncryptionService`) and are never included in this model's normal serialization — see
    `EmailConnectionOut` in `app/schemas/email_tracking.py`, which simply has no token fields."""

    __tablename__ = "email_connections"
    __table_args__ = (
        # A given external mailbox account can only ever be linked to one CareerOS user — prevents
        # a stolen/shared OAuth code from silently attaching someone else's mailbox to an attacker's
        # account, and makes provider-account collisions impossible to hit by accident.
        UniqueConstraint("provider", "provider_account_id", name="uq_email_connection_provider_account"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    provider: Mapped[EmailProvider] = mapped_column(Enum(EmailProvider), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str] = mapped_column(String(255), nullable=False)

    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    status: Mapped[EmailConnectionStatus] = mapped_column(
        Enum(EmailConnectionStatus), nullable=False, default=EmailConnectionStatus.ACTIVE
    )

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Gmail-specific sync cursors (spec §7/§59) — null for OUTLOOK connections.
    gmail_history_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gmail_watch_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Outlook-specific subscription bookkeeping (spec §11/§58) — null for GMAIL connections.
    outlook_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outlook_subscription_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecruitmentEmailEvent(TimestampMixin, Base):
    """A single recruitment-relevant message CareerOS has seen, plus whatever it inferred from it.
    Never the source of a stage change by itself — see module docstring."""

    __tablename__ = "recruitment_email_events"
    __table_args__ = (
        # The idempotency guarantee from spec §9/§42: the same provider message can never produce
        # two rows for the same user, no matter how many times a webhook redelivers it.
        UniqueConstraint("user_id", "provider", "provider_message_id", name="uq_recruitment_event_dedup"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email_connection_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("email_connections.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[EmailProvider] = mapped_column(Enum(EmailProvider), nullable=False)

    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    # A short, sanitized excerpt only — never the full email body (spec §18: data minimization).
    # Kept solely so the confirmation UI can show "detected because ... 'invited to complete an
    # online assessment' was detected" without CareerOS retaining a shadow mailbox.
    evidence_excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    matched_application_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    # Populated only when status == AMBIGUOUS — the candidate application ids the matcher couldn't
    # distinguish between (spec §25). The user's own `assign-application` call picks one of these.
    candidate_application_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    detected_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(20), nullable=True)  # HIGH/MEDIUM/LOW
    classification_reason_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[RecruitmentEventStatus] = mapped_column(
        Enum(RecruitmentEventStatus), nullable=False, default=RecruitmentEventStatus.DETECTED
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OAuthState(Base):
    """A one-time, short-lived CSRF token for the OAuth authorization-code flow (spec §44). The
    browser-redirected callback endpoint has no CareerOS bearer token available (Google/Microsoft
    redirect the user's browser directly to it) — this table is what lets that callback recover
    *which* CareerOS user and provider initiated the flow, safely. `consumed_at` being set makes a
    state value permanently unusable after its first (successful or failed) callback, closing the
    replay window spec §44 calls out."""

    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[EmailProvider] = mapped_column(Enum(EmailProvider), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailForwardingAlias(TimestampMixin, Base):
    """Spec §36 — the "Forward to CareerOS" alternative. `alias_token` is a long random opaque
    string, never a sequential/guessable user id, so the alias itself leaks nothing about the
    account it belongs to."""

    __tablename__ = "email_forwarding_aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    alias_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
