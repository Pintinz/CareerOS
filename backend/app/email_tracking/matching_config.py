"""Centralized configuration for the application-matching engine and the classifier's confidence
model (spec §24 "Do not use arbitrary weights scattered through code. Put configuration centrally"
and spec §26). Nothing outside this module should hardcode a matching weight or confidence
threshold.
"""

# Application-matching weights (spec §24's example table, used verbatim). Every signal is scored
# 0..weight and the total is normalized to a 0..1 "match strength" per candidate application.
MATCH_WEIGHTS: dict[str, int] = {
    "job_or_reference_id": 35,
    "company_domain": 20,
    "job_title": 20,
    "reference_id": 15,  # kept distinct from job_or_reference_id: an explicit "Ref: ABC123" hit.
    "timing": 5,
    "location": 5,
}
MATCH_WEIGHT_TOTAL = sum(MATCH_WEIGHTS.values())

# A candidate application must clear this normalized score to be considered a match at all. Set
# low enough that "company matched, nothing else" (score 0.20 — exactly the ambiguous scenario in
# spec §25: a generic same-company invitation with no role evidence) still qualifies as *a*
# candidate — MATCH_AMBIGUITY_MARGIN is what then decides whether that's one confident match or
# several tied candidates needing the user to pick.
MATCH_MIN_SCORE = 0.2

# Two (or more) candidates within this fraction of each other's score are "too close to call" —
# spec §25's ambiguous-match rule. Never silently pick the higher-scoring one when it's this close.
MATCH_AMBIGUITY_MARGIN = 0.15

# Confidence-score contributions (spec §26). These are added, then clamped to 0..1.
CONFIDENCE_WEIGHTS: dict[str, float] = {
    "application_identifier_match": 0.30,
    "company_match": 0.15,
    "role_match": 0.15,
    "stage_language_strength": 0.25,
    "recipient_directed_language": 0.15,
    "known_ats_domain": 0.10,
    "timing_context": 0.05,
}

# Applied (subtracted) whenever a negative-context pattern is present alongside an otherwise
# matching stage phrase (spec §23) — large enough that a general "only shortlisted candidates will
# be contacted" line can never reach SUGGESTED confidence even if other signals are present.
NEGATIVE_CONTEXT_PENALTY = 0.6

# Confidence-label thresholds (spec §26 "High / Medium / Low"). A LOW-confidence event never
# produces a push notification (spec §26) and a below-SUGGEST_MIN event never leaves DETECTED status
# for the user to review at all — it would be more noise than signal.
CONFIDENCE_HIGH = 0.75
CONFIDENCE_MEDIUM = 0.45
SUGGEST_MIN_CONFIDENCE = 0.35


def confidence_label(score: float) -> str:
    if score >= CONFIDENCE_HIGH:
        return "HIGH"
    if score >= CONFIDENCE_MEDIUM:
        return "MEDIUM"
    return "LOW"
