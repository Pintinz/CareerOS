"""Push-delivery provider abstraction (Phase 11, spec §29-32) — mirrors the exact pattern already
established for email tracking (`EmailTrackingProvider`/`MockEmailTrackingProvider`) and
monetization's ad-provider abstraction: one interface, a mock implementation usable end-to-end in
dev, and a real implementation left unimplemented until real credentials exist.

**No real FCM/APNs integration exists.** `FirebaseCloudMessagingProvider` below is a documented
stub, not a working implementation — see DEPLOYMENT.md's "Push notifications" section for exactly
what standing one up would require (a Firebase project, a service-account key, the `firebase-admin`
Python package). `PushService` always uses `MockPushProvider` in this environment; nothing here
sends a real notification to a real device.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("careeros.push")


class PushProvider(ABC):
    @abstractmethod
    async def send(self, *, token: str, title: str, body: str, data: dict | None = None) -> bool:
        """Returns True if the provider accepted the message for delivery. Never raises for a
        single invalid/expired token — callers use the return value to decide whether to mark
        that token inactive (spec §30's "invalid token cleanup")."""
        raise NotImplementedError


class MockPushProvider(PushProvider):
    """Records what *would* have been sent, for tests/dev — delivers nothing to any real device.
    Never logs `body` in full (spec §26/§29: never log sensitive content) — only that a send was
    attempted, its title length, and the outcome."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, *, token: str, title: str, body: str, data: dict | None = None) -> bool:
        logger.info("Mock push send: token=%s... title_len=%d", token[:8], len(title))
        self.sent.append({"token": token, "title": title, "body": body, "data": data})
        return True


class FirebaseCloudMessagingProvider(PushProvider):
    """Documented stub — NOT implemented. Standing this up for real requires:
    1. A real Firebase project with Cloud Messaging enabled.
    2. A service-account JSON key (kept out of Git/Docker images — see DEPLOYMENT.md's secret
       management section) provided via `GOOGLE_APPLICATION_CREDENTIALS` or an equivalent secret
       mount.
    3. The `firebase-admin` Python package (not currently a dependency — intentionally not added
       until this is actually wired up, to avoid an unused dependency).
    4. Real `send()` calls via `firebase_admin.messaging.send()`, plus token-invalidation handling
       for `UNREGISTERED`/`INVALID_ARGUMENT` errors (spec §30).
    See PROJECT_STATUS.md and RELEASE_READINESS.md for this feature's current status: NOT
    IMPLEMENTED, blocked on real Firebase credentials that don't exist in this environment."""

    async def send(self, *, token: str, title: str, body: str, data: dict | None = None) -> bool:
        raise NotImplementedError(
            "Real FCM sending is not implemented in this environment — see DEPLOYMENT.md."
        )
