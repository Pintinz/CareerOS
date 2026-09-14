"""What a user may do with a listing right now (spec §40, §55-56).

`availability` is derived, never stored:
- ACTIVE       published, confirmed at its source, not past its deadline/expiry → Apply is shown
- EXPIRED      deadline or expiry passed, or an editor expired it → "no longer active", no Apply
- CLOSED       the source says applications are closed → no Apply
- UNAVAILABLE  the source removed the listing or couldn't be confirmed → "Listing unavailable"

Feeds only return ACTIVE listings; detail pages stay reachable for saved items and applications.
"""

from datetime import datetime, timezone

from app.models.job import ContentStatus, SourceState, SourceType

ACTIVE = "ACTIVE"
EXPIRED = "EXPIRED"
CLOSED = "CLOSED"
UNAVAILABLE = "UNAVAILABLE"

OFFICIAL_SOURCE_TYPES = {
    SourceType.OFFICIAL_CAREER_PAGE, SourceType.OFFICIAL_NEWSROOM, SourceType.INVESTOR_RELATIONS, SourceType.GOVERNMENT,
    SourceType.REGULATOR, SourceType.UNIVERSITY, SourceType.SCHOLARSHIP_PROVIDER, SourceType.GREENHOUSE, SourceType.LEVER,
    SourceType.ASHBY, SourceType.SMARTRECRUITERS, SourceType.WORKDAY, SourceType.SUCCESSFACTORS, SourceType.ORACLE,
}


def _passed(value: datetime | None, now: datetime) -> bool:
    if value is None:
        return False
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware <= now


def availability_of(row, *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    state = getattr(row, "source_state", SourceState.ACTIVE)
    if state in (SourceState.SOURCE_REMOVED, SourceState.UNKNOWN_REQUIRES_REVIEW):
        return UNAVAILABLE
    if state == SourceState.CLOSED:
        return CLOSED
    if row.status != ContentStatus.PUBLISHED or state in (SourceState.DEADLINE_PASSED, SourceState.EXPIRED):
        return EXPIRED
    if _passed(getattr(row, "application_deadline", None), now) or _passed(getattr(row, "expires_at", None), now):
        return EXPIRED
    return ACTIVE


def is_official_source(row) -> bool:
    """True only for listings whose recorded source is an official organization channel or its
    official ATS — used for a subtle "Official source" label, never inferred from the URL alone."""
    return getattr(row, "source_type", None) in OFFICIAL_SOURCE_TYPES and bool(getattr(row, "source_url", None))


def publicly_listable(row) -> bool:
    return row.status == ContentStatus.PUBLISHED and getattr(row, "is_active", True) and availability_of(row) == ACTIVE


def publicly_viewable(row) -> bool:
    """Detail pages: published (in any source state) or expired; never drafts or archived rows."""
    return getattr(row, "is_active", True) and row.status in (ContentStatus.PUBLISHED, ContentStatus.EXPIRED)
