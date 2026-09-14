"""Thin, append-only audit trail (spec §34). Call `record()` from an admin mutation endpoint after
the mutation succeeds — never before, and never let a logging failure roll back the mutation itself
(the caller commits its own change; `record` does its own commit against the same session but
catches nothing, so a genuine DB error here does surface rather than being silently swallowed,
matching every other service in this codebase)."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_ops import AuditLog


async def record(
    db: AsyncSession,
    *,
    admin_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


def add(
    db: AsyncSession,
    *,
    admin_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Same as `record` but without committing — for background jobs (admin_id None = system) that
    commit their own unit of work, so the audit row lands atomically with the change it describes."""
    db.add(
        AuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
    )
