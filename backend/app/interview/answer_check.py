"""Deterministic "Answer Structure Check" (spec §22-23) — word count, length flags, STAR keyword
hints, presence of a metric. Explicitly not AI analysis and never labeled as such; every signal
here is a plain string/regex check on the user's own typed text."""

import re

from app.interview.scoring import (
    ANSWER_EXCESSIVE_WORD_COUNT,
    ANSWER_MIN_WORD_COUNT,
    ANSWER_SHORT_WORD_COUNT,
    METRIC_INDICATOR_PATTERN,
    STAR_KEYWORD_HINTS,
)


def word_count(text: str) -> int:
    return len(text.split())


def answer_structure_check(text: str) -> dict:
    """Returns a plain-data structure check result — never a score, never "AI feedback"."""
    count = word_count(text)
    lower = text.lower()

    star_hints = {
        section: any(keyword in lower for keyword in keywords) for section, keywords in STAR_KEYWORD_HINTS.items()
    }
    has_metric = bool(re.search(METRIC_INDICATOR_PATTERN, text))

    flags: list[str] = []
    if count < ANSWER_SHORT_WORD_COUNT:
        flags.append("very_short_answer")
    elif count < ANSWER_MIN_WORD_COUNT:
        flags.append("below_recommended_length")
    if count > ANSWER_EXCESSIVE_WORD_COUNT:
        flags.append("excessive_length")
    if not has_metric:
        flags.append("no_measurable_result_detected")
    if not any(star_hints.values()):
        flags.append("no_star_structure_detected")

    return {
        "word_count": count,
        "has_metric": has_metric,
        "star_hints": star_hints,
        "flags": flags,
    }
