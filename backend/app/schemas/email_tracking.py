from datetime import datetime

from pydantic import BaseModel

from app.models.application import ApplicationStage
from app.models.email_tracking import EmailConnectionStatus, EmailProvider, RecruitmentEventStatus


class EmailConnectionOut(BaseModel):
    """Deliberately has no token fields at all — not even encrypted ones (spec §16 "do not
    expose encrypted blobs via normal API serialization"). There is no `access_token`/
    `refresh_token` attribute on this schema for a client to accidentally receive."""

    id: str
    provider: EmailProvider
    provider_email: str
    status: EmailConnectionStatus
    granted_scopes: list[str]
    last_sync_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_code: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderAvailabilityOut(BaseModel):
    """Backs the settings screen's provider cards (spec §38) — lets the client show "Connect" vs.
    "In development" without guessing from a failed API call."""

    gmail_available: bool
    outlook_available: bool
    forward_email_available: bool
    forward_email_alias: str | None = None


class ConnectStartOut(BaseModel):
    authorization_url: str


class RecruitmentEmailEventOut(BaseModel):
    id: str
    provider: EmailProvider
    sender_email: str
    sender_domain: str
    sender_name: str | None = None
    subject: str
    evidence_excerpt: str | None = None
    received_at: datetime
    matched_application_id: str | None = None
    candidate_application_ids: list[str] = []
    detected_stage: ApplicationStage | None = None
    confidence_score: float | None = None
    confidence_label: str | None = None
    classification_reason_json: dict = {}
    status: RecruitmentEventStatus
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AssignApplicationIn(BaseModel):
    application_id: str


class GmailWebhookIn(BaseModel):
    """Google Pub/Sub push-subscription envelope. `message.data` is base64 of a JSON payload
    shaped like `{"emailAddress": "...", "historyId": "..."}` — see
    `app/api/v1/webhooks.py::_decode_gmail_pubsub_message`."""

    message: dict
    subscription: str | None = None
