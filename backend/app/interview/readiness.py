"""Deterministic interview-readiness calculation (spec §11/§25) — every component is derived from
real stored activity counts passed in by the caller. Never a random or invented percentage. When a
component genuinely doesn't apply (e.g. no application/company context), it's excluded and the
remaining weights are renormalized rather than silently counted as zero."""

from app.interview.scoring import (
    JOB_SPECIFIC_QUESTION_TARGET,
    MIN_ACTIVITY_FOR_READINESS,
    QUESTION_PRACTICE_TARGET,
    READINESS_WEIGHTS,
    STAR_STORY_TARGET,
    TECHNICAL_QUESTION_TARGET,
)


def _capped_percentage(count: int, target: int) -> float:
    if target <= 0:
        return 0.0
    return min(100.0, round((count / target) * 100, 1))


def _recency_percentage(days_since_last_practice: int | None) -> float:
    if days_since_last_practice is None:
        return 0.0
    if days_since_last_practice <= 2:
        return 100.0
    if days_since_last_practice <= 7:
        return 75.0
    if days_since_last_practice <= 14:
        return 40.0
    if days_since_last_practice <= 30:
        return 10.0
    return 0.0


def compute_readiness(
    *,
    questions_practiced: int,
    star_ready_count: int,
    technical_questions_practiced: int,
    days_since_last_practice: int | None,
    company_checklist_done: int | None = None,
    company_checklist_total: int = 0,
    job_specific_questions_practiced: int | None = None,
) -> dict:
    total_signal = questions_practiced + star_ready_count
    if total_signal < MIN_ACTIVITY_FOR_READINESS:
        return {
            "overall": None,
            "insufficient_data": True,
            "components": {
                "question_practice": None,
                "star_coverage": None,
                "company_prep": None,
                "job_specific_prep": None,
                "technical_prep": None,
                "recent_consistency": None,
            },
        }

    components: dict[str, float | None] = {
        "question_practice": _capped_percentage(questions_practiced, QUESTION_PRACTICE_TARGET),
        "star_coverage": _capped_percentage(star_ready_count, STAR_STORY_TARGET),
        "technical_prep": _capped_percentage(technical_questions_practiced, TECHNICAL_QUESTION_TARGET),
        "recent_consistency": _recency_percentage(days_since_last_practice),
        "company_prep": (
            _capped_percentage(company_checklist_done, company_checklist_total)
            if company_checklist_done is not None and company_checklist_total > 0
            else None
        ),
        "job_specific_prep": (
            _capped_percentage(job_specific_questions_practiced, JOB_SPECIFIC_QUESTION_TARGET)
            if job_specific_questions_practiced is not None
            else None
        ),
    }

    applicable_weights = {key: weight for key, weight in READINESS_WEIGHTS.items() if components[key] is not None}
    total_weight = sum(applicable_weights.values())
    if total_weight <= 0:
        overall = None
    else:
        overall = round(
            sum(components[key] * (weight / total_weight) for key, weight in applicable_weights.items()), 1
        )

    return {"overall": overall, "insufficient_data": False, "components": components}
