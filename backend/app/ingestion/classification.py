"""Deterministic, conservative classification of discovered listings (spec §10, §12).

Rules err towards "ordinary job": a listing becomes a GRADUATE_PROGRAM only with an explicit
programme marker and no experienced-hire marker, and an INTERNSHIP only when the ATS says so or
the title explicitly does. Unclear work modes stay UNSPECIFIED; nothing is inferred from a
company's reputation or a location's typical practice.
"""

from __future__ import annotations

import re

_GRADUATE_MARKERS = re.compile(
    r"\b(graduate\s+(programme|program|scheme|trainee(ship)?|development\s+programme|development\s+program|intake|rotation)"
    r"|management\s+trainee(\s+programme|\s+program)?|early[\s-]careers?\s+(programme|program)"
    r"|trainee\s+(programme|program)|new\s+grad(uate)?\s+program(me)?|graduate\s+engineer\s+trainee)",
    re.IGNORECASE,
)
_EXPERIENCED_MARKERS = re.compile(
    r"\b(senior|sr\.?|lead|principal|staff|manager|head\s+of|director|chief|vp|vice\s+president|architect"
    r"|\d+\s*\+?\s*years?)\b",
    re.IGNORECASE,
)
_INTERNSHIP_MARKERS = re.compile(
    r"\b(intern|interns|internship|internships|industrial\s+training|siwes|placement\s+year|year\s+in\s+industry"
    r"|co-?op|work\s+placement|summer\s+placement)\b",
    re.IGNORECASE,
)

_ENTRY_MARKERS = re.compile(r"\b(entry[\s-]level|junior|jr\.?|associate|trainee|apprentice|graduate)\b", re.IGNORECASE)
_SENIOR_MARKERS = re.compile(r"\b(senior|sr\.?)\b", re.IGNORECASE)
_LEAD_MARKERS = re.compile(r"\b(lead|principal|staff|head\s+of|manager)\b", re.IGNORECASE)
_EXECUTIVE_MARKERS = re.compile(r"\b(director|chief|vp|vice\s+president|cxo|ceo|cto|cfo|coo)\b", re.IGNORECASE)


def classify_job_content_type(title: str, *, employment_type: str | None = None, text: str | None = None) -> str:
    if _GRADUATE_MARKERS.search(title) and not _EXPERIENCED_MARKERS.search(title):
        return "GRADUATE_PROGRAM"
    if employment_type == "INTERNSHIP" or _INTERNSHIP_MARKERS.search(title):
        return "INTERNSHIP"
    return "JOB"


def experience_level_from_title(title: str) -> str | None:
    """Only when the title itself states seniority. Otherwise None (never assumed MID)."""
    if _EXECUTIVE_MARKERS.search(title):
        return "EXECUTIVE"
    if _SENIOR_MARKERS.search(title):
        return "SENIOR"
    if _LEAD_MARKERS.search(title):
        return "LEAD"
    if _ENTRY_MARKERS.search(title):
        return "ENTRY"
    return None


_WORK_MODE_MAP = {
    "remote": "REMOTE", "fully remote": "REMOTE", "remote-first": "REMOTE", "telecommute": "REMOTE",
    "hybrid": "HYBRID",
    "on-site": "ON_SITE", "onsite": "ON_SITE", "on site": "ON_SITE", "in-office": "ON_SITE", "in office": "ON_SITE",
    "office": "ON_SITE",
}


def normalize_work_mode(value: str | None) -> str:
    if not value:
        return "UNSPECIFIED"
    key = re.sub(r"[_\s]+", " ", str(value)).strip().lower()
    key = key.replace("onsite", "on-site") if key == "onsite" else key
    compact = key.replace(" ", "")
    for candidate in (key, compact, key.replace(" ", "-")):
        if candidate in _WORK_MODE_MAP:
            return _WORK_MODE_MAP[candidate]
    return "UNSPECIFIED"


_EMPLOYMENT_MAP = {
    "fulltime": "FULL_TIME", "full time": "FULL_TIME", "full-time": "FULL_TIME", "permanent": "FULL_TIME", "regular": "FULL_TIME",
    "parttime": "PART_TIME", "part time": "PART_TIME", "part-time": "PART_TIME",
    "contract": "CONTRACT", "contractor": "CONTRACT", "fixed term": "CONTRACT", "fixed-term": "CONTRACT", "freelance": "CONTRACT",
    "intern": "INTERNSHIP", "internship": "INTERNSHIP",
    "temporary": "TEMPORARY", "temp": "TEMPORARY", "seasonal": "TEMPORARY",
    "volunteer": "VOLUNTEER",
}


def normalize_employment_type(value: str | None) -> str | None:
    if not value:
        return None
    key = re.sub(r"[_]+", " ", str(value)).strip().lower()
    if key in _EMPLOYMENT_MAP:
        return _EMPLOYMENT_MAP[key]
    compact = key.replace(" ", "").replace("-", "")
    return _EMPLOYMENT_MAP.get(compact)


_SALARY_PERIOD_MAP = {
    "per-year-salary": "yearly", "year": "yearly", "yearly": "yearly", "annual": "yearly", "annually": "yearly",
    "per-month-salary": "monthly", "month": "monthly", "monthly": "monthly",
    "per-week-salary": "weekly", "week": "weekly", "weekly": "weekly",
    "per-day-salary": "daily", "day": "daily", "daily": "daily",
    "per-hour-wage": "hourly", "hour": "hourly", "hourly": "hourly",
}


def normalize_salary_period(value: str | None) -> str | None:
    if not value:
        return None
    return _SALARY_PERIOD_MAP.get(str(value).strip().lower())


def split_location(location: str | None) -> tuple[str | None, str | None, str | None]:
    """'Lagos, Lagos State, Nigeria' → (city, region, country). Only splits comma-separated
    values; a single token is kept as the location only (not assumed to be a country)."""
    if not location:
        return None, None, None
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[-1]
    if len(parts) == 2:
        # "Austin, TX": a two-letter code is a region, not a country.
        if len(parts[1]) == 2 and parts[1].isupper():
            return parts[0], parts[1], None
        return parts[0], None, parts[1]
    return None, None, None
