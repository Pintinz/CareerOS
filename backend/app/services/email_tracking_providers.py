"""Provider abstraction for Phase 8 (spec §5): one interface, three implementations, so nothing
Google- or Microsoft-specific ever leaks into `email_tracking_service.py` or the API routers.

`GmailTrackingProvider`/`OutlookTrackingProvider` are structurally real — real OAuth endpoints,
real token exchange, real Gmail/Graph API calls via `httpx` — but have never been exercised against
an actual Google/Microsoft account in this environment, since no production OAuth credentials are
configured here (see PROJECT_STATUS.md's completion report). `MockEmailTrackingProvider` is what
every test in this codebase (and the mobile "mock connect flow") actually runs against, and is also
what the backend falls back to for a provider whose real credentials aren't configured, so the
feature stays fully usable in dev — see `get_provider()` at the bottom of this file.
"""

from __future__ import annotations

import base64
import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.email_tracking.types import RawEmail

GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
# Minimum read-only scope genuinely required (spec §4) — never gmail.modify/send/compose.
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

MS_AUTH_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MS_TOKEN_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
# Delegated, read-only, current-user-mailbox-only (spec §10) — never Mail.ReadWrite/Send, never an
# application (tenant-wide) permission grant.
MS_SCOPES = "offline_access Mail.Read User.Read"


@dataclass(frozen=True)
class ProviderTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes: list[str]
    provider_account_id: str
    provider_email: str


@dataclass(frozen=True)
class WatchInfo:
    """Gmail calls this a "watch" (historyId + expiration); Outlook calls it a "subscription"
    (subscriptionId + expirationDateTime). Same shape either way from the service's perspective."""

    cursor: str  # Gmail historyId, or a sentinel for Outlook (which uses delta links instead).
    external_id: str | None  # Outlook subscription id; unused (None) for Gmail.
    expires_at: datetime


class EmailTrackingProvider(ABC):
    """One mailbox provider's OAuth + message-fetch + watch/subscription lifecycle. See module
    docstring for which concrete classes are real vs. mock."""

    @abstractmethod
    def build_authorization_url(self, *, state: str) -> str: ...

    @abstractmethod
    async def exchange_code(self, *, code: str) -> ProviderTokens: ...

    @abstractmethod
    async def refresh_access_token(self, *, refresh_token: str) -> ProviderTokens: ...

    @abstractmethod
    async def establish_watch(self, *, access_token: str) -> WatchInfo: ...

    @abstractmethod
    async def renew_watch(self, *, access_token: str, current_cursor: str) -> WatchInfo: ...

    @abstractmethod
    async def list_changed_message_ids(self, *, access_token: str, cursor: str) -> tuple[list[str], str]:
        """Returns (new_message_ids, new_cursor). Never re-scans the whole mailbox (spec §7)."""

    @abstractmethod
    async def fetch_message(self, *, access_token: str, message_id: str) -> RawEmail: ...

    @abstractmethod
    async def revoke(self, *, access_token: str, refresh_token: str | None) -> None: ...


class GmailTrackingProvider(EmailTrackingProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_authorization_url(self, *, state: str) -> str:
        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": self._settings.google_redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SCOPE,
            "access_type": "offline",  # required to receive a refresh_token.
            "prompt": "consent",
            "state": state,
        }
        return f"{GMAIL_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, *, code: str) -> ProviderTokens:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                GMAIL_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "redirect_uri": self._settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            profile_response = await client.get(
                f"{GMAIL_API_BASE}/users/me/profile",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
        return ProviderTokens(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600)),
            scopes=token_data.get("scope", "").split(),
            provider_account_id=str(profile["historyId"]),
            provider_email=profile["emailAddress"],
        )

    async def refresh_access_token(self, *, refresh_token: str) -> ProviderTokens:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                GMAIL_TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            data = response.json()
        return ProviderTokens(
            access_token=data["access_token"],
            refresh_token=refresh_token,  # Google only reissues a refresh token occasionally.
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600)),
            scopes=data.get("scope", "").split(),
            provider_account_id="",
            provider_email="",
        )

    async def establish_watch(self, *, access_token: str) -> WatchInfo:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GMAIL_API_BASE}/users/me/watch",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"topicName": self._settings.google_pubsub_topic, "labelIds": ["INBOX"]},
            )
            response.raise_for_status()
            data = response.json()
        return WatchInfo(
            cursor=str(data["historyId"]),
            external_id=None,
            expires_at=datetime.fromtimestamp(int(data["expiration"]) / 1000, tz=timezone.utc),
        )

    async def renew_watch(self, *, access_token: str, current_cursor: str) -> WatchInfo:
        return await self.establish_watch(access_token=access_token)

    async def list_changed_message_ids(self, *, access_token: str, cursor: str) -> tuple[list[str], str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GMAIL_API_BASE}/users/me/history",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"startHistoryId": cursor, "historyTypes": "messageAdded"},
            )
            if response.status_code == 404:
                # Spec §7/§9 — a stale/expired historyId. Caller must re-establish a watch and
                # accept that some history may be unrecoverable, not crash.
                raise StaleSyncCursorError("Gmail historyId is stale or invalid")
            response.raise_for_status()
            data = response.json()
        message_ids = [
            record["message"]["id"]
            for history_record in data.get("history", [])
            for record in history_record.get("messagesAdded", [])
        ]
        new_cursor = str(data.get("historyId", cursor))
        return message_ids, new_cursor

    async def fetch_message(self, *, access_token: str, message_id: str) -> RawEmail:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GMAIL_API_BASE}/users/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"},
            )
            response.raise_for_status()
            data = response.json()
        headers = {h["name"].lower(): h["value"] for h in data["payload"].get("headers", [])}
        return RawEmail(
            provider_message_id=data["id"],
            provider_thread_id=data.get("threadId"),
            sender_email=_extract_email_address(headers.get("from", "")),
            sender_name=_extract_display_name(headers.get("from", "")),
            subject=headers.get("subject", ""),
            body_text=_extract_gmail_body_text(data["payload"]),
            received_at=datetime.fromtimestamp(int(data.get("internalDate", 0)) / 1000, tz=timezone.utc),
        )

    async def revoke(self, *, access_token: str, refresh_token: str | None) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post("https://oauth2.googleapis.com/revoke", params={"token": refresh_token or access_token})


class OutlookTrackingProvider(EmailTrackingProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_authorization_url(self, *, state: str) -> str:
        params = {
            "client_id": self._settings.microsoft_client_id,
            "redirect_uri": self._settings.microsoft_redirect_uri,
            "response_type": "code",
            "response_mode": "query",
            "scope": MS_SCOPES,
            "state": state,
        }
        auth_url = MS_AUTH_URL_TMPL.format(tenant=self._settings.microsoft_tenant)
        return f"{auth_url}?{urlencode(params)}"

    async def exchange_code(self, *, code: str) -> ProviderTokens:
        token_url = MS_TOKEN_URL_TMPL.format(tenant=self._settings.microsoft_tenant)
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                token_url,
                data={
                    "client_id": self._settings.microsoft_client_id,
                    "client_secret": self._settings.microsoft_client_secret,
                    "code": code,
                    "redirect_uri": self._settings.microsoft_redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": MS_SCOPES,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            profile_response = await client.get(
                f"{GRAPH_API_BASE}/me", headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
        return ProviderTokens(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600)),
            scopes=token_data.get("scope", "").split(),
            provider_account_id=profile["id"],
            provider_email=profile.get("mail") or profile.get("userPrincipalName", ""),
        )

    async def refresh_access_token(self, *, refresh_token: str) -> ProviderTokens:
        token_url = MS_TOKEN_URL_TMPL.format(tenant=self._settings.microsoft_tenant)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": self._settings.microsoft_client_id,
                    "client_secret": self._settings.microsoft_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": MS_SCOPES,
                },
            )
            response.raise_for_status()
            data = response.json()
        return ProviderTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600)),
            scopes=data.get("scope", "").split(),
            provider_account_id="",
            provider_email="",
        )

    async def establish_watch(self, *, access_token: str) -> WatchInfo:
        expires_at = datetime.now(timezone.utc) + timedelta(days=2)  # Graph mail subscriptions cap at ~4230 min.
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/subscriptions",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "changeType": "created",
                    "notificationUrl": self._settings.microsoft_webhook_url,
                    "lifecycleNotificationUrl": self._settings.microsoft_lifecycle_webhook_url,
                    "resource": "me/mailFolders('Inbox')/messages",
                    "expirationDateTime": expires_at.isoformat(),
                    "clientState": secrets.token_urlsafe(24),
                },
            )
            response.raise_for_status()
            data = response.json()
        return WatchInfo(cursor="", external_id=data["id"], expires_at=datetime.fromisoformat(data["expirationDateTime"]))

    async def renew_watch(self, *, access_token: str, current_cursor: str) -> WatchInfo:
        # `current_cursor` here is actually the subscription id for Outlook (see WatchInfo docstring).
        new_expiry = datetime.now(timezone.utc) + timedelta(days=2)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{GRAPH_API_BASE}/subscriptions/{current_cursor}",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"expirationDateTime": new_expiry.isoformat()},
            )
            response.raise_for_status()
            data = response.json()
        return WatchInfo(cursor="", external_id=data["id"], expires_at=datetime.fromisoformat(data["expirationDateTime"]))

    async def list_changed_message_ids(self, *, access_token: str, cursor: str) -> tuple[list[str], str]:
        # Outlook notifications carry the changed message's id directly (spec §11) — reconciliation
        # sync (spec §12 "missed notifications") instead lists recent inbox messages.
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/me/mailFolders('Inbox')/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"$top": 25, "$orderby": "receivedDateTime desc", "$select": "id"},
            )
            response.raise_for_status()
            data = response.json()
        return [item["id"] for item in data.get("value", [])], cursor

    async def fetch_message(self, *, access_token: str, message_id: str) -> RawEmail:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"$select": "id,conversationId,from,subject,bodyPreview,body,receivedDateTime"},
            )
            response.raise_for_status()
            data = response.json()
        sender = data.get("from", {}).get("emailAddress", {})
        return RawEmail(
            provider_message_id=data["id"],
            provider_thread_id=data.get("conversationId"),
            sender_email=sender.get("address", ""),
            sender_name=sender.get("name"),
            subject=data.get("subject", ""),
            body_text=data.get("bodyPreview", ""),  # plain-text preview only — never raw HTML (spec §43).
            received_at=datetime.fromisoformat(data["receivedDateTime"].replace("Z", "+00:00")),
        )

    async def revoke(self, *, access_token: str, refresh_token: str | None) -> None:
        # Microsoft has no token-revocation endpoint equivalent to Google's; disconnecting deletes
        # the Graph subscription (see email_tracking_service.disconnect) and drops our copy of the
        # tokens, which is the practical equivalent for a delegated-permission app.
        return None


class StaleSyncCursorError(Exception):
    """Gmail's historyId (or, conceptually, an Outlook delta cursor) is too old for the API to
    resolve — spec §9's "history gap" failure mode. Callers must fall back to re-establishing a
    fresh watch rather than crashing or looping forever."""


class MockEmailTrackingProvider(EmailTrackingProvider):
    """Deterministic, in-memory provider used by every automated test and by the mobile "mock
    connect flow" acceptance test (spec §65-66/§39). Never makes a network call. Tests push
    messages into `.inbox` and this class hands them back exactly like a real provider would.
    """

    def __init__(self) -> None:
        self.inbox: dict[str, RawEmail] = {}
        self._history: list[str] = []
        self.revoked: list[str] = []

    def seed_message(self, email: RawEmail) -> None:
        self.inbox[email.provider_message_id] = email
        self._history.append(email.provider_message_id)

    def build_authorization_url(self, *, state: str) -> str:
        return f"https://mock-provider.careeros.test/authorize?state={state}"

    async def exchange_code(self, *, code: str) -> ProviderTokens:
        return ProviderTokens(
            access_token=f"mock-access-{uuid.uuid4()}",
            refresh_token=f"mock-refresh-{uuid.uuid4()}",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["mock.readonly"],
            provider_account_id=f"mock-account-{uuid.uuid4()}",
            provider_email="mock.user@example.com",
        )

    async def refresh_access_token(self, *, refresh_token: str) -> ProviderTokens:
        return ProviderTokens(
            access_token=f"mock-access-{uuid.uuid4()}",
            refresh_token=refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["mock.readonly"],
            provider_account_id="",
            provider_email="",
        )

    async def establish_watch(self, *, access_token: str) -> WatchInfo:
        return WatchInfo(cursor="0", external_id=f"mock-sub-{uuid.uuid4()}", expires_at=datetime.now(timezone.utc) + timedelta(days=2))

    async def renew_watch(self, *, access_token: str, current_cursor: str) -> WatchInfo:
        return WatchInfo(cursor=current_cursor, external_id=f"mock-sub-{uuid.uuid4()}", expires_at=datetime.now(timezone.utc) + timedelta(days=2))

    async def list_changed_message_ids(self, *, access_token: str, cursor: str) -> tuple[list[str], str]:
        already_seen = int(cursor) if cursor.isdigit() else 0
        new_ids = self._history[already_seen:]
        return new_ids, str(len(self._history))

    async def fetch_message(self, *, access_token: str, message_id: str) -> RawEmail:
        return self.inbox[message_id]

    async def revoke(self, *, access_token: str, refresh_token: str | None) -> None:
        self.revoked.append(access_token)


def _extract_email_address(from_header: str) -> str:
    if "<" in from_header and ">" in from_header:
        return from_header.split("<", 1)[1].split(">", 1)[0].strip()
    return from_header.strip()


def _extract_display_name(from_header: str) -> str | None:
    if "<" in from_header:
        name = from_header.split("<", 1)[0].strip().strip('"')
        return name or None
    return None


def _extract_gmail_body_text(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _b64url_decode(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _b64url_decode(part["body"]["data"])
    for part in payload.get("parts", []) or []:
        text = _extract_gmail_body_text(part)
        if text:
            return text
    return ""


def _b64url_decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
