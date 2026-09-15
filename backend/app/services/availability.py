"""What a user may do with a listing right now (spec §40, §55-56).

`availability` is derived, never stored:
- ACTIVE       published, confirmed at its source, not past its deadline/expiry → Apply is shown
- EXPIRED      deadline or expiry passed, or an editor expired it → "no longer active", no Apply
- CLOSED       the source says applications are closed → no Apply
- UNAVAILABLE  the source removed the listing or couldn't be confirmed → "Listing unavailable"

Feeds only return ACTIVE listings; detail pages stay reachable for saved items and applications.
"""

from datetime import datetime, timedelta, timezone

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


ATS_SOURCE_TYPES = {
    SourceType.GREENHOUSE, SourceType.LEVER, SourceType.ASHBY, SourceType.SMARTRECRUITERS, SourceType.WORKDAY,
    SourceType.SUCCESSFACTORS, SourceType.ORACLE,
}
# A listing not re-confirmed at its source for this long is labelled STALE rather than verified.
STALE_AFTER = timedelta(days=7)


def verification_status_of(row, *, now: datetime | None = None) -> str:
    """Provenance label shown with a listing: OFFICIAL_ATS / OFFICIAL_SOURCE while recently confirmed
    at an official source, STALE when that confirmation is old, SOURCE_REMOVED when the source no
    longer lists it, VERIFIED for editor-verified entries, UNVERIFIED otherwise. Never claims a
    verification CareerOS doesn't have evidence for."""
    now = now or datetime.now(timezone.utc)
    if getattr(row, "source_state", None) == SourceState.SOURCE_REMOVED:
        return "SOURCE_REMOVED"
    if is_official_source(row):
        checked = getattr(row, "last_verified_at", None)
        if checked is None:
            return "VERIFIED" if getattr(row, "is_verified", False) else "UNVERIFIED"
        checked = checked if checked.tzinfo else checked.replace(tzinfo=timezone.utc)
        if now - checked > STALE_AFTER:
            return "STALE"
        return "OFFICIAL_ATS" if getattr(row, "source_type", None) in ATS_SOURCE_TYPES else "OFFICIAL_SOURCE"
    return "VERIFIED" if getattr(row, "is_verified", False) else "UNVERIFIED"


def publicly_listable(row) -> bool:
    return row.status == ContentStatus.PUBLISHED and getattr(row, "is_active", True) and availability_of(row) == ACTIVE


def publicly_viewable(row) -> bool:
    """Detail pages: published (in any source state) or expired; never drafts or archived rows."""
    return getattr(row, "is_active", True) and row.status in (ContentStatus.PUBLISHED, ContentStatus.EXPIRED)
