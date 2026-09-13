"""Deterministic default category distributions for a role-linked Mock Interview's "Automatic
Mix" (spec §8-9). Centralized here — not scattered across mobile widgets — so the mix logic is
shared by every client and testable in one place. Percentages are CareerOS product heuristics
for balanced practice coverage, not a claim about what any real employer's interview actually
covers."""

from app.interview.job_role_topic_map import JOB_ROLE_INTERVIEW_TOPIC_MAP

# (keyword set, {category_slug: fraction}) — fractions per entry sum to 1.0.
ROLE_DEFAULT_MIX: list[tuple[set[str], dict[str, float]]] = [
    (
        {
            "process technician", "process operator", "refinery", "oil & gas", "oil and gas",
            "petrochemical", "mechanical engineer", "manufacturing", "maintenance", "operations",
        },
        {"technical": 0.40, "behavioral": 0.25, "safety": 0.20, "hr_general": 0.15},
    ),
    (
        {
            "software engineer", "software developer", "backend engineer", "frontend engineer",
            "data analyst", "data science", "machine learning", "ai engineer", "cybersecurity",
        },
        {"technical": 0.50, "behavioral": 0.25, "situational": 0.15, "hr_general": 0.10},
    ),
    (
        {"management", "team lead", "supervisor", "manager", "operations manager"},
        {"leadership": 0.30, "behavioral": 0.25, "management": 0.25, "situational": 0.10, "hr_general": 0.10},
    ),
]

# Used when no role keywords match anything above — a balanced general-purpose mix.
GENERAL_DEFAULT_MIX: dict[str, float] = {
    "behavioral": 0.30,
    "hr_general": 0.25,
    "situational": 0.20,
    "technical": 0.15,
    "career_motivation": 0.10,
}


def default_mix_for(*, field: str | None, industry: str | None, job_role: str | None) -> dict[str, float]:
    """Returns {category_slug: fraction} summing to 1.0. Falls back to a general mix when the
    role doesn't match a known keyword set — reuses the same haystack-matching approach as
    `job_role_topic_map.topics_for` for consistency."""
    haystack = " ".join(filter(None, [field, industry, job_role])).lower()
    if haystack.strip():
        for keywords, mix in ROLE_DEFAULT_MIX:
            if any(keyword in haystack for keyword in keywords):
                return mix
    return GENERAL_DEFAULT_MIX


def category_counts_for_mix(mix: dict[str, float], total_questions: int) -> dict[str, int]:
    """Converts fractions into whole-number question counts that sum exactly to
    `total_questions` — largest-remainder rounding so no category silently drops to zero when
    its fraction is small but non-zero relative to the total."""
    raw = {slug: fraction * total_questions for slug, fraction in mix.items()}
    counts = {slug: int(value) for slug, value in raw.items()}
    remainder = total_questions - sum(counts.values())
    remainders = sorted(raw.items(), key=lambda item: item[1] - int(item[1]), reverse=True)
    for slug, _ in remainders[:remainder]:
        counts[slug] += 1
    return counts


# Re-exported for callers that only need to know which topic keywords exist, without importing
# the topic-map module directly.
__all__ = ["default_mix_for", "category_counts_for_mix", "ROLE_DEFAULT_MIX", "GENERAL_DEFAULT_MIX", "JOB_ROLE_INTERVIEW_TOPIC_MAP"]
