import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, event, func, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm.attributes import set_committed_value


class Base(DeclarativeBase):
    """Shared declarative base. Import every model module in migrations/env.py so Alembic
    autogenerate can see them."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def new_uuid() -> str:
    return str(uuid.uuid4())


def _mark_loaded_datetimes_utc(target) -> None:
    """Every timestamp column is `DateTime(timezone=True)` and stored in UTC. PostgreSQL returns
    aware values, but SQLite (local development, tests) drops the offset and returns naive ones —
    which the API would then serialize without a timezone, so a client in e.g. Lagos (UTC+1) reads
    "18:00" as local time and a test timer looks an hour further along than it is. Tag them as UTC
    on load without marking the object dirty."""
    for attr in inspect(target).mapper.column_attrs:
        column = attr.columns[0]
        if not (isinstance(column.type, DateTime) and column.type.timezone):
            continue
        value = target.__dict__.get(attr.key)
        if isinstance(value, datetime) and value.tzinfo is None:
            set_committed_value(target, attr.key, value.replace(tzinfo=timezone.utc))


@event.listens_for(Base, "load", propagate=True)
def _utc_on_load(target, _context) -> None:
    _mark_loaded_datetimes_utc(target)


@event.listens_for(Base, "refresh", propagate=True)
def _utc_on_refresh(target, _context, _attrs) -> None:
    _mark_loaded_datetimes_utc(target)
