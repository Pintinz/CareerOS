"""Deterministic ATS Readiness / Job Match engine (master spec §15).

Everything here is string/regex/frequency-based. No LLM call, no "AI" of any kind — the result
must always be described to users as rules-based similarity scoring (spec Rule 8), and every
score comes with a breakdown naming the weighted components that produced it (ARCHITECTURE.md
-> Scoring engines) so nothing is a bare, unexplained percentage.
"""

import re
from dataclasses import dataclass, field

from app.matching.ats_weights import AtsWeights, DEFAULT_ATS_WEIGHTS
from app.matching.text_utils import extract_keywords, find_years_of_experience, keyword_coverage, normalize

TECHNICAL_SKILLS_VOCAB = {
    "python", "java", "javascript", "typescript", "sql", "excel", "power bi", "tableau",
    "aws", "azure", "gcp", "docker", "kubernetes", "react", "flutter", "dart", "django",
    "fastapi", "node.js", "git", "ci/cd", "terraform", "linux", "plc", "scada", "dcs",
    "p&id", "hvac", "hse", "loto", "autocad", "solidworks", "matlab", "salesforce", "sap",
    "machine learning", "data analysis", "statistics", "figma", "photoshop",
}

EDUCATION_TERMS = {
    "bachelor", "master", "phd", "doctorate", "bsc", "msc", "mba", "b.eng", "m.eng",
    "diploma", "degree", "university", "college", "certification", "certified",
}

_SECTION_HEADERS = {
    "experience": ["experience", "work experience", "employment history", "professional experience"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "technical skills", "core competencies"],
    "contact": ["email", "phone", "linkedin"],
    "summary": ["summary", "objective", "profile"],
}

_BULLET_RE = re.compile(r"^\s*[•\-\*•]\s+", re.MULTILINE)
_METRIC_RE = re.compile(r"\d+%|\$\d|\d+x\b|\bincreased\b|\breduced\b|\bimproved\b", re.IGNORECASE)


@dataclass
class AtsAnalysisResult:
    overall_score: int
    keyword_match_score: int
    technical_skills_score: int
    experience_score: int
    job_title_score: int
    formatting_score: int
    education_score: int
    completeness_score: int
    placement_score: int

    strong_matches: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    formatting_issues: list[str] = field(default_factory=list)
    missing_metrics_note: str | None = None

    def score_breakdown(self, weights: AtsWeights) -> dict[str, dict[str, float]]:
        return {
            "keyword_match": {"score": self.keyword_match_score, "weight": weights.keyword_match},
            "technical_skills": {"score": self.technical_skills_score, "weight": weights.technical_skills},
            "experience": {"score": self.experience_score, "weight": weights.experience},
            "job_title": {"score": self.job_title_score, "weight": weights.job_title},
            "formatting": {"score": self.formatting_score, "weight": weights.formatting},
            "education": {"score": self.education_score, "weight": weights.education},
            "completeness": {"score": self.completeness_score, "weight": weights.completeness},
            "placement": {"score": self.placement_score, "weight": weights.placement},
        }


def analyze(
    *,
    cv_text: str,
    job_description: str,
    job_title: str | None = None,
    weights: AtsWeights = DEFAULT_ATS_WEIGHTS,
) -> AtsAnalysisResult:
    jd_keywords = extract_keywords(job_description, top_n=25)

    keyword_ratio, matched, missing = keyword_coverage(cv_text, jd_keywords)

    jd_technical = [kw for kw in jd_keywords if kw in TECHNICAL_SKILLS_VOCAB] or list(
        TECHNICAL_SKILLS_VOCAB & set(extract_keywords(job_description, top_n=100))
    )
    technical_ratio, _, _ = keyword_coverage(cv_text, jd_technical) if jd_technical else (1.0, [], [])

    experience_ratio = _score_experience(cv_text, job_description)
    title_ratio = _score_job_title(cv_text, job_title)
    formatting_ratio, formatting_issues = _score_formatting(cv_text)
    education_ratio = _score_education(cv_text, job_description)
    completeness_ratio, missing_sections = _score_completeness(cv_text)
    placement_ratio = _score_placement(cv_text, jd_keywords)

    if missing_sections:
        formatting_issues.append(f"Missing sections: {', '.join(missing_sections)}")

    result = AtsAnalysisResult(
        overall_score=0,
        keyword_match_score=round(keyword_ratio * 100),
        technical_skills_score=round(technical_ratio * 100),
        experience_score=round(experience_ratio * 100),
        job_title_score=round(title_ratio * 100),
        formatting_score=round(formatting_ratio * 100),
        education_score=round(education_ratio * 100),
        completeness_score=round(completeness_ratio * 100),
        placement_score=round(placement_ratio * 100),
        strong_matches=matched[:10],
        missing_keywords=missing[:10],
        formatting_issues=formatting_issues,
        missing_metrics_note=(
            "No quantified achievements detected (numbers, %, or impact verbs like "
            "'increased'/'reduced'/'improved') — bullet points with metrics score better."
            if not _METRIC_RE.search(cv_text)
            else None
        ),
    )

    overall = (
        keyword_ratio * weights.keyword_match
        + technical_ratio * weights.technical_skills
        + experience_ratio * weights.experience
        + title_ratio * weights.job_title
        + formatting_ratio * weights.formatting
        + education_ratio * weights.education
        + completeness_ratio * weights.completeness
        + placement_ratio * weights.placement
    )
    result.overall_score = round(overall * 100)
    return result


def _score_experience(cv_text: str, job_description: str) -> float:
    required_years = find_years_of_experience(job_description)
    candidate_years = find_years_of_experience(cv_text)

    if required_years is None:
        # No explicit requirement to check against — credit any demonstrated experience.
        return 1.0 if candidate_years is not None else 0.5
    if candidate_years is None:
        return 0.3
    if candidate_years >= required_years:
        return 1.0
    return max(0.0, candidate_years / required_years)


def _score_job_title(cv_text: str, job_title: str | None) -> float:
    if not job_title:
        return 1.0  # nothing to compare against — don't penalize
    ratio, _, _ = keyword_coverage(cv_text, normalize(job_title).split())
    return ratio


def _score_formatting(cv_text: str) -> tuple[float, list[str]]:
    issues: list[str] = []
    checks_passed = 0
    total_checks = 4

    if _BULLET_RE.search(cv_text):
        checks_passed += 1
    else:
        issues.append("No bullet points detected — ATS parsers and recruiters both favor scannable bullets.")

    word_count = len(cv_text.split())
    if 150 <= word_count <= 1200:
        checks_passed += 1
    else:
        issues.append(
            "CV length looks unusual "
            + ("(too short)" if word_count < 150 else "(too long)")
            + f" — {word_count} words; aim for roughly 300-900."
        )

    caps_words = re.findall(r"\b[A-Z]{4,}\b", cv_text)
    if len(caps_words) < 10:
        checks_passed += 1
    else:
        issues.append("Excessive ALL-CAPS text can trip up ATS parsers — use normal casing with bold/headers instead.")

    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", cv_text):
        checks_passed += 1
    else:
        issues.append("No email address detected — make sure contact info is in plain text, not an image.")

    return checks_passed / total_checks, issues


def _score_education(cv_text: str, job_description: str) -> float:
    jd_normalized = normalize(job_description)
    relevant_terms = [term for term in EDUCATION_TERMS if term in jd_normalized]
    if not relevant_terms:
        return 1.0  # JD didn't specify — don't penalize
    ratio, _, _ = keyword_coverage(cv_text, relevant_terms)
    return ratio


def _score_completeness(cv_text: str) -> tuple[float, list[str]]:
    normalized = normalize(cv_text)
    missing = []
    present = 0
    for section, aliases in _SECTION_HEADERS.items():
        if any(alias in normalized for alias in aliases):
            present += 1
        else:
            missing.append(section)
    return present / len(_SECTION_HEADERS), missing


def _score_placement(cv_text: str, jd_keywords: list[str]) -> float:
    """Rewards keywords appearing early in the document (first third) — a real, if simple,
    proxy for "is this keyword prominent" rather than buried at the very end."""
    if not jd_keywords:
        return 1.0
    normalized = normalize(cv_text)
    if not normalized:
        return 0.0
    early_slice = normalized[: max(1, len(normalized) // 3)]
    early_hits = sum(1 for kw in jd_keywords if kw in early_slice)
    return early_hits / len(jd_keywords)
