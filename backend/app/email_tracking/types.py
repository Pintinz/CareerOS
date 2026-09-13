"""Shared plain-data types passed between providers → classifier → matcher → service. Kept as a
single module so none of those layers need to import each other's internals."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RawEmail:
    """A normalized view of one provider message, already stripped of anything provider-specific
    (Gmail's MIME parts vs. Graph's JSON body are both flattened to this by the provider layer
    before the message ever reaches the classifier). `body_text` is processed transiently — see
    `app/services/email_tracking_service.py` for exactly what is, and is not, persisted from it."""

    provider_message_id: str
    provider_thread_id: str | None
    sender_email: str
    sender_name: str | None
    subject: str
    body_text: str
    received_at: datetime


@dataclass(frozen=True)
class ApplicationSignal:
    """The subset of one `Application` row the matcher needs — a plain dataclass (not the ORM
    model) so `app/email_tracking/matcher.py` has zero SQLAlchemy dependency and can be unit
    tested with plain Python objects, no database required."""

    application_id: str
    company_name: str
    role_title: str
    job_url: str | None
    location: str | None
    applied_date: datetime | None


@dataclass(frozen=True)
class MatchCandidate:
    application_id: str
    score: float
    evidence: list[str] = field(default_factory=list)
    # Keys from `matching_config.CONFIDENCE_WEIGHTS` this candidate satisfied — lets the service
    # layer compute confidence without parsing human-readable evidence strings.
    signals: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class MatchResult:
    """`status` is one of "matched" / "ambiguous" / "unmatched" — never a raw guess. `matched_id`
    is set only for "matched"; `candidate_ids` is set only for "ambiguous" (spec §25)."""

    status: str
    matched_id: str | None
    candidate_ids: list[str]
    evidence: list[str]
    signals: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ClassificationResult:
    candidate_stage: str | None
    confidence_score: float
    confidence_label: str
    evidence: list[str]
    is_recruitment_related: bool
