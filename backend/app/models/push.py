import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class DevicePlatform(str, enum.Enum):
    ANDROID = "ANDROID"
    IOS = "IOS"


class DeviceToken(TimestampMixin, Base):
    """Phase 11 (spec §29-30) — persisted push-notification device tokens. Architecture only:
    no real FCM/APNs credentials exist in this environment (see DEPLOYMENT.md), so nothing ever
    actually sends through these tokens yet; `MockPushProvider` is the only registered provider.
    Supports multiple devices per user (a phone + a tablet both stay registered independently) and
    survives logout/re-login on the same device (the token itself is device-scoped, not
    session-scoped — a fresh login just re-upserts the same row via the unique constraint below)."""

    __tablename__ = "device_tokens"
    __table_args__ = (UniqueConstraint("platform", "token", name="uq_device_tokens_platform_token"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[DevicePlatform] = mapped_column(Enum(DevicePlatform), nullable=False)
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationPreferences(TimestampMixin, Base):
    """One row per user (spec §31) — categories a user can individually disable. Defaults to all
    categories enabled; a user who never visits notification settings still gets everything,
    matching how every other opt-out-style preference in this codebase defaults (e.g. email
    tracking's provider cards default to available-but-not-connected, never silently on)."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    application_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deadlines: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    job_matches: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scholarships: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    company_intelligence: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preparation_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
