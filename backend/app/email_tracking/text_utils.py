"""Small, dependency-free text-normalization helpers shared by the classifier and matcher.
Deliberately not a full NLP stack (spec §21: "Phase 8 must work without generative AI") — just
enough normalization to make phrase/token matching reliable across real-world formatting noise.
"""

import re
from datetime import datetime, timezone

_WHITESPACE_RE = re.compile(r"\s+")
_REFERENCE_TOKEN_RE = re.compile(r"\b[A-Za-z]{0,4}-?\d{3,}[A-Za-z]?\b")
_COMPANY_SUFFIXES = re.compile(
    r"\b(ltd|limited|inc|incorporated|llc|plc|corp|corporation|co|company|group)\.?\b", re.IGNORECASE
)


def normalize(text: str | None) -> str:
    """Lowercase + collapse whitespace. The one normalization every classifier/matcher check runs
    text through before comparing, so callers never have to remember to do it themselves."""
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def extract_reference_tokens(text: str) -> set[str]:
    """Pulls out alphanumeric-with-digits tokens that look like a job/application reference
    number (e.g. "REQ12345", "2024-8817", "AB1234C") — used for the job_or_reference_id and
    reference_id matching signals (spec §24)."""
    return {m.group(0).lower() for m in _REFERENCE_TOKEN_RE.finditer(text)}


def company_slug(name: str) -> str:
    """Strips common corporate suffixes and non-alphanumerics so "Shell Oil Company" and "Shell"
    compare equal-ish for domain/sender matching."""
    slug = _COMPANY_SUFFIXES.sub("", name.lower())
    return re.sub(r"[^a-z0-9]", "", slug)


def as_aware_utc(value: datetime) -> datetime:
    """SQLite (used in tests and local dev) doesn't actually enforce `DateTime(timezone=True)` —
    values round-trip as naive. Treat a naive value as UTC rather than letting a naive/aware
    comparison raise, matching the pattern already established in `interview_service.py`."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def word_overlap_ratio(a: str, b: str) -> float:
    """Fraction of `a`'s significant words (len > 2) that also appear in `b`. Used for job-title
    matching — deliberately order-independent and typo-tolerant only at the whole-word level (spec
    §49 covers minor role-title variance, not full fuzzy matching)."""
    words_a = {w for w in normalize(a).split() if len(w) > 2}
    if not words_a:
        return 0.0
    words_b = set(normalize(b).split())
    return len(words_a & words_b) / len(words_a)
