"""Configurable thresholds for the aptitude engine (spec §23/§27) — kept in one place, same
pattern as `app/matching/ats_weights.py`."""

# Mixed-difficulty distribution (spec §10). If the bank doesn't have enough at a given
# difficulty, the generator fills the shortfall from other difficulties rather than erroring.
MIXED_DIFFICULTY_DISTRIBUTION = {
    "EASY": 0.30,
    "MEDIUM": 0.45,
    "HARD": 0.20,
    "EXPERT": 0.05,
}

# Percentage bands for the qualitative performance label (spec §23 — never a random pass/fail).
PERFORMANCE_THRESHOLDS = [
    (75.0, "Strong Performance"),
    (50.0, "Good Performance"),
]
PERFORMANCE_LABEL_BELOW_THRESHOLDS = "Needs Improvement"

# A topic needs at least this many attempted questions across a user's history before its
# accuracy is used for weak-topic recommendations (spec §27 — avoid misleading small samples).
MIN_ATTEMPTS_FOR_TOPIC_RECOMMENDATION = 3
WEAK_TOPIC_ACCURACY_THRESHOLD = 60.0
MAX_WEAK_TOPICS_RETURNED = 5


def performance_label(percentage: float) -> str:
    for threshold, label in PERFORMANCE_THRESHOLDS:
        if percentage >= threshold:
            return label
    return PERFORMANCE_LABEL_BELOW_THRESHOLDS
