from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_tracking import (
    EmailConnection,
    EmailForwardingAlias,
    EmailProvider,
    OAuthState,
    RecruitmentEmailEvent,
    RecruitmentEventStatus,
)


class EmailConnectionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user_id: str) -> list[EmailConnection]:
        result = await self.db.execute(
            select(EmailConnection)
            .where(EmailConnection.user_id == user_id, EmailConnection.disconnected_at.is_(None))
            .order_by(EmailConnection.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_owned(self, connection_id: str, user_id: str) -> EmailConnection | None:
        result = await self.db.execute(
            select(EmailConnection).where(EmailConnection.id == connection_id, EmailConnection.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_provider(self, user_id: str, provider: EmailProvider) -> EmailConnection | None:
        result = await self.db.execute(
            select(EmailConnection).where(
                EmailConnection.user_id == user_id,
                EmailConnection.provider == provider,
                EmailConnection.disconnected_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_all_active(self, provider: EmailProvider | None = None) -> list[EmailConnection]:
        """Every non-disconnected connection, across all users — used by the daily watch/
        subscription renewal jobs (spec §58-59), never by a per-user-authenticated endpoint."""
        query = select(EmailConnection).where(EmailConnection.disconnected_at.is_(None))
        if provider is not None:
            query = query.where(EmailConnection.provider == provider)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def add(self, connection: EmailConnection) -> EmailConnection:
        self.db.add(connection)
        return connection


class RecruitmentEmailEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(
        self, user_id: str, *, application_id: str | None = None, needs_review_only: bool = False
    ) -> list[RecruitmentEmailEvent]:
        query = select(RecruitmentEmailEvent).where(RecruitmentEmailEvent.user_id == user_id)
        if application_id is not None:
            query = query.where(RecruitmentEmailEvent.matched_application_id == application_id)
        if needs_review_only:
            query = query.where(
                RecruitmentEmailEvent.status.in_([RecruitmentEventStatus.SUGGESTED, RecruitmentEventStatus.AMBIGUOUS])
            )
        query = query.order_by(RecruitmentEmailEvent.received_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_owned(self, event_id: str, user_id: str) -> RecruitmentEmailEvent | None:
        result = await self.db.execute(
            select(RecruitmentEmailEvent).where(
                RecruitmentEmailEvent.id == event_id, RecruitmentEmailEvent.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def count_needing_review(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(RecruitmentEmailEvent)
            .where(
                RecruitmentEmailEvent.user_id == user_id,
                RecruitmentEmailEvent.status.in_([RecruitmentEventStatus.SUGGESTED, RecruitmentEventStatus.AMBIGUOUS]),
            )
        )
        return result.scalar_one()

    async def try_add(self, event: RecruitmentEmailEvent) -> RecruitmentEmailEvent | None:
        """Returns None (instead of raising) on a duplicate (user, provider, provider_message_id)
        — the idempotency guarantee from spec §9/§42. Uses a SAVEPOINT so the caller's outer
        transaction survives a duplicate without needing to roll back everything else it did."""
        try:
            async with self.db.begin_nested():
                self.db.add(event)
                await self.db.flush()
        except IntegrityError:
            return None
        return event


class OAuthStateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, state: OAuthState) -> OAuthState:
        self.db.add(state)
        return state

    async def get(self, state: str) -> OAuthState | None:
        result = await self.db.execute(select(OAuthState).where(OAuthState.state == state))
        return result.scalar_one_or_none()

    async def mark_consumed(self, state: OAuthState, *, when: datetime) -> None:
        state.consumed_at = when
        await self.db.flush()


class EmailForwardingAliasRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_user(self, user_id: str) -> EmailForwardingAlias | None:
        result = await self.db.execute(select(EmailForwardingAlias).where(EmailForwardingAlias.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_token(self, alias_token: str) -> EmailForwardingAlias | None:
        result = await self.db.execute(
            select(EmailForwardingAlias).where(EmailForwardingAlias.alias_token == alias_token)
        )
        return result.scalar_one_or_none()

    def add(self, alias: EmailForwardingAlias) -> EmailForwardingAlias:
        self.db.add(alias)
        return alias
