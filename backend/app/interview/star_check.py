"""Deterministic STAR completeness check (spec §15) — no AI grading. Each of the four sections is
independently checked for presence and a minimum length; the result names concrete gaps
("Missing measurable outcome", "Very short Action", etc.) rather than a single opaque score."""

import re

from app.interview.scoring import STAR_FIELD_MIN_LENGTH

_METRIC_PATTERN = re.compile(r"\d")
_FIRST_PERSON_PATTERN = re.compile(r"\bI\b", re.IGNORECASE)


def _section_status(text: str | None) -> str:
    if not text or not text.strip():
        return "missing"
    if len(text.strip()) < STAR_FIELD_MIN_LENGTH:
        return "brief"
    return "complete"


def star_completeness_check(*, situation: str | None, task: str | None, action: str | None, result: str | None) -> dict:
    situation_status = _section_status(situation)
    task_status = _section_status(task)
    action_status = _section_status(action)
    result_status = _section_status(result)

    # Action gets an extra "strong" tier: complete AND shows clear personal contribution ("I ...").
    if action_status == "complete":
        action_status = "strong" if action and _FIRST_PERSON_PATTERN.search(action) else "complete"

    gaps: list[str] = []
    if situation_status == "missing":
        gaps.append("no_situation")
    if task_status == "missing":
        gaps.append("no_task")
    if action_status == "missing":
        gaps.append("no_action")
    elif action_status == "brief":
        gaps.append("very_short_action")
    elif action_status == "complete":
        gaps.append("no_clear_personal_contribution")
    if result_status == "missing":
        gaps.append("no_result")
    elif result and not _METRIC_PATTERN.search(result):
        gaps.append("missing_measurable_outcome")

    sections = {"situation": situation_status, "task": task_status, "action": action_status, "result": result_status}
    is_complete = all(status != "missing" for status in sections.values())

    return {"sections": sections, "gaps": gaps, "is_complete": is_complete}
