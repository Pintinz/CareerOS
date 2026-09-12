"""Deterministic (rules-based, not AI) interview question selection engine (spec §8/§17)."""

import random

from app.interview.job_role_topic_map import topics_for
from app.interview.scoring import JUNIOR_EXPERIENCE_LEVELS, MIXED_DIFFICULTY_DISTRIBUTION
from app.models.interview import InterviewDifficulty, InterviewQuestion
from app.repositories.interview_repository import InterviewQuestionRepository, sample_without_replacement


def _excluded_difficulties(difficulty: str, experience_level: str | None) -> list[InterviewDifficulty]:
    if difficulty == "MIXED" and experience_level in JUNIOR_EXPERIENCE_LEVELS:
        return [InterviewDifficulty.EXPERT]
    return []


async def generate_questions(
    repo: InterviewQuestionRepository,
    *,
    category_ids: list[str],
    difficulty: str,
    question_count: int,
    field: str | None = None,
    industry: str | None = None,
    job_role: str | None = None,
    company_id: str | None = None,
    experience_level: str | None = None,
    category_counts: dict[str, int] | None = None,
) -> list[InterviewQuestion]:
    """Returns up to `question_count` distinct active questions. Never raises for an under-stocked
    bank — returns the best available valid set instead. `category_counts` (category_id -> exact
    count), when given, overrides even distribution — this is how the Mock Interview builder asks
    for e.g. Technical 4 / Behavioral 3 / Safety 2 / HR 1 (spec §17)."""

    topic_slugs = topics_for(field=field, industry=industry, job_role=job_role)
    exclude_difficulties = _excluded_difficulties(difficulty, experience_level)

    selected: list[InterviewQuestion] = []
    exclude_ids: set[str] = set()

    if category_counts:
        for category_id, count in category_counts.items():
            if count <= 0:
                continue
            picked = await _select_for_category(
                repo,
                category_id=category_id,
                difficulty=difficulty,
                exclude_difficulties=exclude_difficulties,
                count=count,
                topic_slugs=topic_slugs,
                company_id=company_id,
                exclude_ids=exclude_ids,
            )
            selected.extend(picked)
            exclude_ids.update(q.id for q in picked)
    else:
        active_categories = category_ids or []
        if not active_categories:
            selected = await _select_for_category(
                repo,
                category_id=None,
                difficulty=difficulty,
                exclude_difficulties=exclude_difficulties,
                count=question_count,
                topic_slugs=topic_slugs,
                company_id=company_id,
                exclude_ids=exclude_ids,
            )
        else:
            base_count, remainder = divmod(question_count, len(active_categories))
            for index, category_id in enumerate(active_categories):
                count = base_count + (1 if index < remainder else 0)
                if count <= 0:
                    continue
                picked = await _select_for_category(
                    repo,
                    category_id=category_id,
                    difficulty=difficulty,
                    exclude_difficulties=exclude_difficulties,
                    count=count,
                    topic_slugs=topic_slugs,
                    company_id=company_id,
                    exclude_ids=exclude_ids,
                )
                selected.extend(picked)
                exclude_ids.update(q.id for q in picked)

            # A category came up short — backfill from any other requested category rather than
            # under-delivering the requested total (spec §8's "best available valid set").
            if len(selected) < question_count:
                need = question_count - len(selected)
                fallback = await _select_for_category(
                    repo,
                    category_id=None,
                    difficulty=difficulty,
                    exclude_difficulties=exclude_difficulties,
                    count=need,
                    topic_slugs=topic_slugs,
                    company_id=company_id,
                    exclude_ids=exclude_ids,
                    category_ids=active_categories,
                )
                selected.extend(fallback)

    random.shuffle(selected)
    return selected[:question_count] if not category_counts else selected


async def _select_for_category(
    repo: InterviewQuestionRepository,
    *,
    category_id: str | None,
    difficulty: str,
    exclude_difficulties: list[InterviewDifficulty],
    count: int,
    topic_slugs: list[str],
    company_id: str | None,
    exclude_ids: set[str],
    category_ids: list[str] | None = None,
) -> list[InterviewQuestion]:
    ids = category_ids if category_ids is not None else ([category_id] if category_id else None)

    if difficulty == "MIXED":
        selected: list[InterviewQuestion] = []
        local_exclude = set(exclude_ids)
        for difficulty_name, ratio in MIXED_DIFFICULTY_DISTRIBUTION.items():
            if InterviewDifficulty(difficulty_name) in exclude_difficulties:
                continue
            target = round(count * ratio)
            if target <= 0:
                continue
            picked = await _select_with_preference(
                repo,
                category_ids=ids,
                difficulty=InterviewDifficulty(difficulty_name),
                exclude_difficulties=exclude_difficulties,
                count=target,
                topic_slugs=topic_slugs,
                company_id=company_id,
                exclude_ids=local_exclude,
            )
            selected.extend(picked)
            local_exclude.update(q.id for q in picked)

        if len(selected) < count:
            need = count - len(selected)
            fallback = await _select_with_preference(
                repo,
                category_ids=ids,
                difficulty=None,
                exclude_difficulties=exclude_difficulties,
                count=need,
                topic_slugs=topic_slugs,
                company_id=company_id,
                exclude_ids=local_exclude,
            )
            selected.extend(fallback)
        return selected[:count]

    return await _select_with_preference(
        repo,
        category_ids=ids,
        difficulty=InterviewDifficulty(difficulty),
        exclude_difficulties=exclude_difficulties,
        count=count,
        topic_slugs=topic_slugs,
        company_id=company_id,
        exclude_ids=exclude_ids,
    )


async def _select_with_preference(
    repo: InterviewQuestionRepository,
    *,
    category_ids: list[str] | None,
    difficulty: InterviewDifficulty | None,
    exclude_difficulties: list[InterviewDifficulty],
    count: int,
    topic_slugs: list[str],
    company_id: str | None,
    exclude_ids: set[str],
) -> list[InterviewQuestion]:
    if count <= 0:
        return []

    # Topic bias and company bias are independent preferences, not a combined requirement — a
    # job-specific session shouldn't fail to prefer "Pumps" questions just because none of them
    # happen to be tagged to that job's company. Try progressively looser tiers rather than
    # ANDing both filters into one query.
    tiers: list[dict[str, list[str] | str | None]] = []
    if topic_slugs and company_id:
        tiers.append({"topic_slugs": topic_slugs, "company_id": company_id})
    if topic_slugs:
        tiers.append({"topic_slugs": topic_slugs, "company_id": None})
    if company_id:
        tiers.append({"topic_slugs": None, "company_id": company_id})
    tiers.append({"topic_slugs": None, "company_id": None})

    picked: list[InterviewQuestion] = []
    exclude = set(exclude_ids)
    for tier in tiers:
        if len(picked) >= count:
            break
        candidates = await repo.candidates_for_selection(
            category_ids=category_ids,
            difficulty=difficulty,
            exclude_difficulties=exclude_difficulties,
            topic_slugs=tier["topic_slugs"],
            company_id=tier["company_id"],
            exclude_ids=exclude,
        )
        need = count - len(picked)
        chosen = sample_without_replacement(candidates, min(len(candidates), need))
        picked.extend(chosen)
        exclude.update(q.id for q in chosen)

    return picked
