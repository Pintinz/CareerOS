from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push import DevicePlatform, DeviceToken, NotificationPreferences
from app.repositories.push_repository import DeviceTokenRepository, NotificationPreferencesRepository
from app.services.push_provider import MockPushProvider, PushProvider


class PushService:
    def __init__(self, db: AsyncSession, *, provider: PushProvider | None = None) -> None:
        self.db = db
        self.tokens = DeviceTokenRepository(db)
        self.preferences = NotificationPreferencesRepository(db)
        # Always the mock in this environment — see app/services/push_provider.py's module
        # docstring for exactly what real FCM/APNs wiring would require.
        self.provider = provider or MockPushProvider()

    async def register_token(self, user_id: str, *, platform: DevicePlatform, token: str) -> DeviceToken:
        """Upserts by (platform, token) — spec §30's "token refresh": a device re-registering the
        same token just refreshes ownership/last_seen rather than creating a duplicate row, and
        correctly re-assigns it if the same physical token is now used by a different logged-in
        user (e.g. a shared device, or after a full uninstall/reinstall+different-account)."""
        existing = await self.tokens.get_by_platform_and_token(platform, token)
        now = datetime.now(timezone.utc)
        if existing is not None:
            existing.user_id = user_id
            existing.is_active = True
            existing.last_seen_at = now
            await self.db.commit()
            return existing

        device_token = DeviceToken(user_id=user_id, platform=platform, token=token, last_seen_at=now)
        self.db.add(device_token)
        await self.db.commit()
        await self.db.refresh(device_token)
        return device_token

    async def unregister_token(self, user_id: str, token: str) -> None:
        """Called on logout (spec §30) — deactivates rather than deletes, so a token accidentally
        reused later fails safe (inactive) instead of silently resurrecting."""
        await self.tokens.deactivate(user_id, token)
        await self.db.commit()

    async def get_preferences(self, user_id: str) -> NotificationPreferences:
        prefs = await self.preferences.get_or_create(user_id)
        await self.db.commit()
        return prefs

    async def update_preferences(self, user_id: str, **updates: bool) -> NotificationPreferences:
        prefs = await self.preferences.get_or_create(user_id)
        for key, value in updates.items():
            if value is not None:
                setattr(prefs, key, value)
        await self.db.commit()
        await self.db.refresh(prefs)
        return prefs
