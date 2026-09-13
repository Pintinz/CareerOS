"""CSV bulk import for the aptitude and interview question banks (spec §20-21). Every row is
validated independently — a broken row is reported with its reason and never imported, and the
rows that do pass validation are still checked for exact/near-duplicate text against the existing
bank before being written, so a bad or duplicate-heavy file can never corrupt the bank silently.
"""

import csv
import io
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewQuestion, InterviewQuestionCategory, InterviewTopic
from app.models.question import Question, QuestionCategory, QuestionOption, QuestionTopic
from app.schemas.aptitude import QuestionCreate, QuestionOptionIn
from app.schemas.interview import InterviewQuestionCreate


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[dict] = field(default_factory=list)
    duplicate_warnings: list[dict] = field(default_factory=list)


async def _resolve_category_id(db: AsyncSession, model, slug: str) -> str | None:
    result = await db.execute(select(model).where(model.slug == slug))
    row = result.scalar_one_or_none()
    return row.id if row else None


async def _resolve_topic_id(db: AsyncSession, model, slug: str | None) -> str | None:
    if not slug:
        return None
    result = await db.execute(select(model).where(model.slug == slug))
    row = result.scalar_one_or_none()
    return row.id if row else None


async def _existing_normalized_texts(db: AsyncSession, model) -> set[str]:
    result = await db.execute(select(model.question_text))
    return {_normalize(text) for (text,) in result.all()}


def _parse_rows(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader)


async def import_aptitude_questions(db: AsyncSession, csv_text: str, *, admin_id: str) -> ImportResult:
    result = ImportResult()
    rows = _parse_rows(csv_text)
    seen_in_file: set[str] = set()
    existing = await _existing_normalized_texts(db, Question)

    for index, row in enumerate(rows, start=2):  # row 1 is the header.
        try:
            question_text = (row.get("question_text") or "").strip()
            if not question_text:
                raise ValueError("question_text is required")
            normalized = _normalize(question_text)
            if normalized in existing or normalized in seen_in_file:
                result.duplicate_warnings.append({"row": index, "question_text": question_text, "reason": "Duplicate or near-identical question text"})
                result.skipped += 1
                continue

            category_id = await _resolve_category_id(db, QuestionCategory, (row.get("category_slug") or "").strip())
            if category_id is None:
                raise ValueError(f"Unknown category_slug '{row.get('category_slug')}'")
            topic_id = await _resolve_topic_id(db, QuestionTopic, (row.get("topic_slug") or "").strip() or None)

            options = []
            for i in range(1, 5):
                text = (row.get(f"option_{i}") or "").strip()
                if not text:
                    continue
                is_correct = (row.get(f"option_{i}_correct") or "").strip().lower() in ("true", "1", "yes")
                options.append(QuestionOptionIn(option_text=text, is_correct=is_correct, display_order=i))

            question_type = (row.get("question_type") or "SINGLE_CHOICE").strip()
            if question_type in ("SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE"):
                correct_count = sum(1 for o in options if o.is_correct)
                if question_type in ("SINGLE_CHOICE", "TRUE_FALSE") and correct_count != 1:
                    raise ValueError(f"{question_type} requires exactly one correct option, found {correct_count}")
                if question_type == "MULTIPLE_CHOICE" and correct_count < 1:
                    raise ValueError("MULTIPLE_CHOICE requires at least one correct option")

            payload = QuestionCreate(
                question_text=question_text,
                question_type=question_type,
                category_id=category_id,
                topic_id=topic_id,
                field=(row.get("field") or "").strip() or None,
                industry=(row.get("industry") or "").strip() or None,
                job_role=(row.get("job_role") or "").strip() or None,
                difficulty=(row.get("difficulty") or "MEDIUM").strip(),
                explanation=(row.get("explanation") or "").strip() or None,
                marks=float(row.get("marks") or 1.0),
                negative_marks=float(row.get("negative_marks") or 0.0),
                options=options,
            )
            question = Question(**payload.model_dump(exclude={"options"}), created_by_admin_id=admin_id)
            db.add(question)
            await db.flush()
            db.add_all(QuestionOption(question_id=question.id, **opt.model_dump()) for opt in payload.options)
            seen_in_file.add(normalized)
            result.imported += 1
        except Exception as exc:  # noqa: BLE001 — every failure reason is surfaced per-row, never silently dropped.
            result.errors.append({"row": index, "reason": str(exc)})

    if result.imported:
        await db.commit()
    return result


async def import_interview_questions(db: AsyncSession, csv_text: str, *, admin_id: str) -> ImportResult:
    result = ImportResult()
    rows = _parse_rows(csv_text)
    seen_in_file: set[str] = set()
    existing = await _existing_normalized_texts(db, InterviewQuestion)

    for index, row in enumerate(rows, start=2):
        try:
            question_text = (row.get("question_text") or "").strip()
            if not question_text:
                raise ValueError("question_text is required")
            normalized = _normalize(question_text)
            if normalized in existing or normalized in seen_in_file:
                result.duplicate_warnings.append({"row": index, "question_text": question_text, "reason": "Duplicate or near-identical question text"})
                result.skipped += 1
                continue

            category_id = await _resolve_category_id(db, InterviewQuestionCategory, (row.get("category_slug") or "").strip())
            if category_id is None:
                raise ValueError(f"Unknown category_slug '{row.get('category_slug')}'")
            topic_id = await _resolve_topic_id(db, InterviewTopic, (row.get("topic_slug") or "").strip() or None)

            evaluation_points = [p.strip() for p in (row.get("evaluation_points") or "").split("|") if p.strip()]
            payload = InterviewQuestionCreate(
                question_text=question_text,
                category_id=category_id,
                topic_id=topic_id,
                field=(row.get("field") or "").strip() or None,
                industry=(row.get("industry") or "").strip() or None,
                job_role=(row.get("job_role") or "").strip() or None,
                difficulty=(row.get("difficulty") or "MEDIUM").strip(),
                evaluation_points=evaluation_points,
                follow_up_prompt=(row.get("follow_up_prompt") or "").strip() or None,
            )
            question = InterviewQuestion(**payload.model_dump(), created_by_admin_id=admin_id)
            db.add(question)
            seen_in_file.add(normalized)
            result.imported += 1
        except Exception as exc:  # noqa: BLE001
            result.errors.append({"row": index, "reason": str(exc)})

    if result.imported:
        await db.commit()
    return result
