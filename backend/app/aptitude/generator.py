"""Deterministic (rules-based, not AI) question selection engine (spec §10-11)."""

import random

from app.aptitude.scoring import MIXED_DIFFICULTY_DISTRIBUTION
from app.aptitude.technical_topic_map import topics_for
from app.models.question import Question, QuestionDifficulty
from app.repositories.question_repository import QuestionRepository


async def generate_questions(
    repo: QuestionRepository,
    *,
    category_ids: list[str],
    difficulty: str,
    question_count: int,
    field: str | None = None,
    industry: str | None = None,
    job_role: str | None = None,
    topic_slugs_override: list[str] | None = None,
) -> list[Question]:
    """Returns up to `question_count` distinct active questions matching the filters. Never
    raises for an under-stocked bank — returns the best available valid set instead (spec §10).

    `topic_slugs_override`, when given, replaces the job/field-derived topic preference entirely
    — this is how "Practice Weak Areas" (spec §27) asks for specific topics directly rather than
    inferring them from a job title."""

    # Job/field-specific runs try to bias Technical-section questions toward relevant topics
    # first, then top up with any other active question if that's not enough.
    topic_slugs = (
        topic_slugs_override
        if topic_slugs_override is not None
        else topics_for(field=field, industry=industry, job_role=job_role)
    )

    if difficulty == "MIXED":
        selected = await _select_mixed_difficulty(
            repo, category_ids=category_ids, question_count=question_count, topic_slugs=topic_slugs
        )
    else:
        selected = await _select_single_difficulty(
            repo,
            category_ids=category_ids,
            difficulty=QuestionDifficulty(difficulty),
            question_count=question_count,
            topic_slugs=topic_slugs,
        )

    random.shuffle(selected)
    return selected


async def _select_with_topic_preference(
    repo: QuestionRepository,
    *,
    category_ids: list[str],
    difficulty: QuestionDifficulty | None,
    count: int,
    topic_slugs: list[str],
    exclude_ids: set[str],
) -> list[Question]:
    if count <= 0:
        return []

    picked: list[Question] = []

    if topic_slugs:
        preferred = await repo.candidates_for_selection(
            category_ids=category_ids, difficulty=difficulty, topic_slugs=topic_slugs, exclude_ids=exclude_ids
        )
        take = min(len(preferred), count)
        picked.extend(random.sample(preferred, take) if take < len(preferred) else preferred)

    if len(picked) < count:
        remaining_exclude = exclude_ids | {q.id for q in picked}
        fallback = await repo.candidates_for_selection(
            category_ids=category_ids, difficulty=difficulty, exclude_ids=remaining_exclude
        )
        need = count - len(picked)
        take = min(len(fallback), need)
        picked.extend(random.sample(fallback, take) if take < len(fallback) else fallback)

    return picked


async def _select_single_difficulty(
    repo: QuestionRepository,
    *,
    category_ids: list[str],
    difficulty: QuestionDifficulty,
    question_count: int,
    topic_slugs: list[str],
) -> list[Question]:
    return await _select_with_topic_preference(
        repo,
        category_ids=category_ids,
        difficulty=difficulty,
        count=question_count,
        topic_slugs=topic_slugs,
        exclude_ids=set(),
    )


async def _select_mixed_difficulty(
    repo: QuestionRepository, *, category_ids: list[str], question_count: int, topic_slugs: list[str]
) -> list[Question]:
    selected: list[Question] = []
    exclude_ids: set[str] = set()

    # First pass: try to hit the target distribution per difficulty.
    for difficulty_name, ratio in MIXED_DIFFICULTY_DISTRIBUTION.items():
        target = round(question_count * ratio)
        if target <= 0:
            continue
        picked = await _select_with_topic_preference(
            repo,
            category_ids=category_ids,
            difficulty=QuestionDifficulty(difficulty_name),
            count=target,
            topic_slugs=topic_slugs,
            exclude_ids=exclude_ids,
        )
        selected.extend(picked)
        exclude_ids.update(q.id for q in picked)

    # Second pass: the bank was short somewhere — fill the shortfall from any remaining
    # active question in the requested categories, regardless of difficulty.
    if len(selected) < question_count:
        need = question_count - len(selected)
        fallback = await _select_with_topic_preference(
            repo,
            category_ids=category_ids,
            difficulty=None,
            count=need,
            topic_slugs=topic_slugs,
            exclude_ids=exclude_ids,
        )
        selected.extend(fallback)

    return selected[:question_count]
