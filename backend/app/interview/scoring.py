"""Configurable thresholds/weights for the interview engine (spec §11/§24/§25) — one place, same
pattern as `app/matching/ats_weights.py` and `app/aptitude/scoring.py`."""

# Mixed-difficulty distribution for question generation (kept separate from the aptitude engine's
# constant of the same shape — the two engines are related in spirit, not coupled in code).
MIXED_DIFFICULTY_DISTRIBUTION = {
    "EASY": 0.30,
    "MEDIUM": 0.45,
    "HARD": 0.20,
    "EXPERT": 0.05,
}

# Experience levels that don't see EXPERT-difficulty questions in a MIXED session unless the user
# explicitly picks EXPERT difficulty (spec §7).
JUNIOR_EXPERIENCE_LEVELS = {"ENTRY", "JUNIOR"}

# Readiness component weights (spec §11) — must sum to 1.0.
READINESS_WEIGHTS = {
    "question_practice": 0.25,
    "star_coverage": 0.25,
    "company_prep": 0.15,
    "job_specific_prep": 0.15,
    "technical_prep": 0.15,
    "recent_consistency": 0.05,
}

# Targets used to turn raw activity counts into a 0-100 completion percentage for each component.
QUESTION_PRACTICE_TARGET = 30  # distinct questions answered/skipped-with-notes across all sessions
STAR_STORY_TARGET = 5  # "ready" (complete) STAR stories
TECHNICAL_QUESTION_TARGET = 15  # distinct TECHNICAL-category questions practiced
JOB_SPECIFIC_QUESTION_TARGET = 10  # distinct job-specific-topic questions practiced for the role

# A STAR story needs each of its four fields to be at least this long to count as "ready"
# (spec §15's completeness check) — short placeholder text doesn't count as complete.
STAR_FIELD_MIN_LENGTH = 20

# Minimum combined signal (questions practiced + STAR stories) before showing a real readiness
# number at all (spec §11/§25 — "Not enough activity to calculate readiness").
MIN_ACTIVITY_FOR_READINESS = 3

# A topic/category needs at least this many attempted questions before its accuracy/coverage is
# used to label a weakness (spec §24 — avoid conclusions from a tiny sample).
MIN_ATTEMPTS_FOR_CATEGORY_BREAKDOWN = 3

# Answer Structure Check thresholds (spec §22-23) — deterministic, never called "AI analysis."
ANSWER_MIN_WORD_COUNT = 40
ANSWER_SHORT_WORD_COUNT = 15
ANSWER_EXCESSIVE_WORD_COUNT = 400
STAR_KEYWORD_HINTS = {
    "situation": ["situation", "context", "background", "at the time", "we had", "there was"],
    "task": ["task", "goal", "objective", "needed to", "responsible for", "had to"],
    "action": ["i did", "i decided", "i implemented", "i led", "i created", "i built", "action"],
    "result": ["result", "outcome", "as a result", "consequently", "this led to", "achieved"],
}
METRIC_INDICATOR_PATTERN = r"\d"
