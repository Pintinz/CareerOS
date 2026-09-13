"""Deterministic recruitment-stage classifier (spec §19-23). No generative AI anywhere in this
module — every decision traces back to a phrase list, a domain list, or a numeric weight, all of
which live in `stage_phrases.py`/`ats_domains.py`/`matching_config.py`.

This module only looks at the *text* of one email — it has no idea which application (if any) it
belongs to. `app/services/email_tracking_service.py` combines this with the matcher's per-candidate
signals to compute a final confidence score for a specific application.
"""

from dataclasses import dataclass

from app.email_tracking.ats_domains import is_known_ats_domain
from app.email_tracking.stage_phrases import (
    GENERAL_RECRUITMENT_VOCABULARY,
    NEGATIVE_CONTEXT_PATTERNS,
    RECIPIENT_DIRECTED_MARKERS,
    STAGE_PHRASES,
)
from app.email_tracking.text_utils import normalize

# More specific / higher-stakes stages are checked first so a message mentioning both "interview"
# and "final interview" language resolves to the more specific one (spec §20's taxonomy order is
# not itself a priority order, so this is defined explicitly rather than left implicit).
_STAGE_PRIORITY = [
    "REJECTED",
    "OFFER",
    "MEDICAL",
    "BACKGROUND_CHECK",
    "ASSESSMENT_CENTRE",
    "FINAL_INTERVIEW",
    "INTERVIEW",
    "RECRUITER_SCREEN",
    "ASSESSMENT_COMPLETED",
    "APTITUDE_TEST",
    "SHORTLISTED",
    "UNDER_REVIEW",
    "APPLICATION_RECEIVED",
]


@dataclass(frozen=True)
class StageClassification:
    stage: str | None
    matched_phrase: str | None
    evidence: list[str]
    has_negative_context: bool
    is_recipient_directed: bool
    is_recruitment_related: bool
    sender_is_known_ats: bool


def classify_stage(*, subject: str, body_text: str, sender_domain: str) -> StageClassification:
    text = normalize(f"{subject} {body_text}")
    sender_is_known_ats = is_known_ats_domain(sender_domain)

    is_recruitment_related = sender_is_known_ats or any(word in text for word in GENERAL_RECRUITMENT_VOCABULARY)

    stage: str | None = None
    matched_phrase: str | None = None
    for candidate_stage in _STAGE_PRIORITY:
        for phrase in STAGE_PHRASES[candidate_stage]:
            if phrase in text:
                stage = candidate_stage
                matched_phrase = phrase
                break
        if stage:
            break

    has_negative_context = any(pattern in text for pattern in NEGATIVE_CONTEXT_PATTERNS)
    is_recipient_directed = any(marker in text for marker in RECIPIENT_DIRECTED_MARKERS)

    evidence: list[str] = []
    if matched_phrase:
        evidence.append(f'"{matched_phrase}" was detected')
        is_recruitment_related = True
    if sender_is_known_ats:
        evidence.append("Sender domain matches a known recruitment/ATS platform")
    if has_negative_context:
        evidence.append("General/non-personal recruitment language detected — treated as informational, not a personal update")

    return StageClassification(
        stage=stage,
        matched_phrase=matched_phrase,
        evidence=evidence,
        has_negative_context=has_negative_context,
        is_recipient_directed=is_recipient_directed,
        is_recruitment_related=is_recruitment_related,
        sender_is_known_ats=sender_is_known_ats,
    )
