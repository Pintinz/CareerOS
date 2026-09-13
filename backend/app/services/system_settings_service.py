"""Runtime-configurable, non-secret settings (spec §35). Each known key has a compiled-in default
(taken from the module that used to be the only source of truth for it) so the admin Settings page
always has something sane to show even before any override is saved, and so a fresh environment
never needs a seed migration for this table to work.

Only `email_classifier_confidence_thresholds` is actually *read* by its consumer in this pass
(`app/email_tracking/confidence.py` via `EmailTrackingService`) — the rest are stored and editable
for visibility/future wiring but the scoring code that used to read the plain module constant still
does; see PROJECT_STATUS.md's Known limitations for the honest accounting of which settings are
"visible and editable" versus "actually consumed at runtime."
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.email_tracking.matching_config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, SUGGEST_MIN_CONFIDENCE
from app.interview.scoring import (
    JOB_SPECIFIC_QUESTION_TARGET,
    QUESTION_PRACTICE_TARGET,
    READINESS_WEIGHTS,
    STAR_STORY_TARGET,
    TECHNICAL_QUESTION_TARGET,
)
from app.matching.ats_weights import DEFAULT_ATS_WEIGHTS
from app.models.admin_ops import SystemSetting

KNOWN_SETTINGS: dict[str, tuple[dict, str]] = {
    "ats_scoring_weights": (DEFAULT_ATS_WEIGHTS.model_dump(), "ATS Readiness Score component weights (must sum to 1.0)."),
    "interview_readiness_weights": (dict(READINESS_WEIGHTS), "Interview readiness component weights (must sum to 1.0)."),
    "interview_readiness_targets": (
        {
            "question_practice": QUESTION_PRACTICE_TARGET,
            "star_story": STAR_STORY_TARGET,
            "technical_question": TECHNICAL_QUESTION_TARGET,
            "job_specific_question": JOB_SPECIFIC_QUESTION_TARGET,
        },
        "Activity counts capped-at for full readiness credit per component.",
    ),
    "email_classifier_confidence_thresholds": (
        {"high": CONFIDENCE_HIGH, "medium": CONFIDENCE_MEDIUM, "suggest_min": SUGGEST_MIN_CONFIDENCE},
        "Recruitment-email classifier confidence label thresholds (0-1). Actually consumed at runtime.",
    ),
    "content_expiry_grace_days": (
        {"days": 0},
        "Days after a deadline/expiry before content is auto-transitioned to EXPIRED by the scheduler.",
    ),
    "notification_defaults": (
        {"quiet_hours_start": 21, "quiet_hours_end": 8},
        "Default local-hour window admin-authored notifications should avoid scheduling into.",
    ),
}


async def get_all(db: AsyncSession) -> dict[str, dict]:
    result = await db.execute(select(SystemSetting))
    overrides = {row.key: row for row in result.scalars().all()}
    merged = {}
    for key, (default_value, description) in KNOWN_SETTINGS.items():
        row = overrides.get(key)
        merged[key] = {
            "value": row.value_json if row else default_value,
            "description": row.description if row else description,
            "updated_at": row.updated_at if row else None,
            "is_default": row is None,
        }
    return merged


async def get_value(db: AsyncSession, key: str) -> dict:
    if key not in KNOWN_SETTINGS:
        raise KeyError(key)
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value_json if row else KNOWN_SETTINGS[key][0]


async def set_value(db: AsyncSession, key: str, value: dict, *, admin_id: str | None) -> None:
    if key not in KNOWN_SETTINGS:
        raise KeyError(key)
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        db.add(
            SystemSetting(
                key=key, value_json=value, description=KNOWN_SETTINGS[key][1], updated_at=now, updated_by_admin_id=admin_id
            )
        )
    else:
        row.value_json = value
        row.updated_at = now
        row.updated_by_admin_id = admin_id
    await db.commit()


async def get_confidence_thresholds(db: AsyncSession) -> tuple[float, float, float]:
    """Returns (high, medium, suggest_min) — the one setting actually wired to its consumer."""
    value = await get_value(db, "email_classifier_confidence_thresholds")
    return value["high"], value["medium"], value["suggest_min"]
