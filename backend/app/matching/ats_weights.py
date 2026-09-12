"""Configurable weights for the ATS Readiness / Job Match score (spec §15).

These are the only numbers that decide the overall score — change them here, not inline in the
engine, so the weighting is auditable in one place and can move to admin-configurable settings
later without touching scoring logic.
"""

from pydantic import BaseModel


class AtsWeights(BaseModel):
    keyword_match: float = 0.25
    technical_skills: float = 0.20
    experience: float = 0.20
    job_title: float = 0.10
    formatting: float = 0.10
    education: float = 0.05
    completeness: float = 0.05
    placement: float = 0.05

    def validate_sums_to_one(self) -> None:
        total = sum(self.model_dump().values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"AtsWeights must sum to 1.0, got {total}")


DEFAULT_ATS_WEIGHTS = AtsWeights()
DEFAULT_ATS_WEIGHTS.validate_sums_to_one()
