"""Combines the classifier's text-only signals with the matcher's per-application signals into one
final confidence score (spec §26-27). Kept as its own tiny module so the "how do these numbers add
up" question has exactly one place to look — see `matching_config.CONFIDENCE_WEIGHTS`.
"""

from app.email_tracking.classifier import StageClassification
from app.email_tracking.matching_config import CONFIDENCE_WEIGHTS, NEGATIVE_CONTEXT_PENALTY, confidence_label


def compute_confidence(stage: StageClassification, match_signals: frozenset[str]) -> tuple[float, str]:
    score = 0.0
    if stage.matched_phrase:
        score += CONFIDENCE_WEIGHTS["stage_language_strength"]
    if stage.is_recipient_directed:
        score += CONFIDENCE_WEIGHTS["recipient_directed_language"]
    if stage.sender_is_known_ats:
        score += CONFIDENCE_WEIGHTS["known_ats_domain"]
    for signal in ("application_identifier_match", "company_match", "role_match", "timing_context"):
        if signal in match_signals:
            score += CONFIDENCE_WEIGHTS[signal]

    if stage.has_negative_context:
        score -= NEGATIVE_CONTEXT_PENALTY

    score = max(0.0, min(1.0, score))
    return score, confidence_label(score)
