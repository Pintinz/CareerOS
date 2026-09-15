"""Deterministic, conservative classification of discovered listings (spec §10, §12).

Rules err towards "ordinary job": a listing becomes a GRADUATE_PROGRAM only with an explicit
programme marker and no experienced-hire marker, and an INTERNSHIP only when the ATS says so or
the title explicitly does. Unclear work modes stay UNSPECIFIED; nothing is inferred from a
company's reputation or a location's typical practice.
"""

from __future__ import annotations

import re

from app.ingestion.countries import match_country

_GRADUATE_MARKERS = re.compile(
    r"\b(graduate\s+(programme|program|scheme|trainee(ship)?|development\s+programme|development\s+program|intake|rotation)"
    r"|early[\s-]careers?\s+(programme|program)|new\s+grad(uate)?\s+program(me)?|graduate\s+engineer\s+trainee)",
    re.IGNORECASE,
)
# Trainee schemes that aren't presented as graduate programmes ("Management Trainee Programme").
_TRAINEE_MARKERS = re.compile(r"\b(management\s+trainee(s)?|trainee\s+(programme|program|scheme))\b", re.IGNORECASE)
_APPRENTICESHIP_MARKERS = re.compile(r"\b(apprentice|apprentices|apprenticeship|apprenticeships|aprendiz|auszubildende[rn]?)\b", re.IGNORECASE)
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
    """From the title (and the source's own employment type) only — explicit markers, never weak
    keyword guesses. Anything led by an experienced-hire marker stays a JOB."""
    experienced = _EXPERIENCED_MARKERS.search(title)
    if _GRADUATE_MARKERS.search(title) and not experienced:
        return "GRADUATE_PROGRAM"
    if _TRAINEE_MARKERS.search(title) and not experienced:
        return "TRAINEE_PROGRAM"
    if _APPRENTICESHIP_MARKERS.search(title) and not experienced:
        return "APPRENTICESHIP"
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


_WORK_MODE_PREFIX = re.compile(r"^\s*(remote|hybrid|home[\s-]based|anywhere)\b[\s:,\-–]*", re.IGNORECASE)
_ALTERNATIVES = re.compile(r";|\||\s+(?:or|and|&)\s+", re.IGNORECASE)
_UNBOUNDED = re.compile(r"\blocations?\s*:|\bmultiple\b|\bvarious\b|\bflexible\b|\banywhere\b", re.IGNORECASE)


def location_work_mode(location: str | None) -> str:
    """REMOTE/HYBRID only when the location string itself leads with it ("Remote, Nigeria",
    "Home based - EMEA"); otherwise UNSPECIFIED (an office city doesn't prove on-site work)."""
    match = _WORK_MODE_PREFIX.match(location or "")
    if not match:
        return "UNSPECIFIED"
    return "HYBRID" if match.group(1).lower() == "hybrid" else "REMOTE"


def split_location(location: str | None) -> tuple[str | None, str | None, str | None]:
    """'Lagos, Lagos State, Nigeria' → (city, region, country).

    A country is only returned when the text names a recognized country — never a placeholder
    ("City, Country") or free text. A listing spanning several places ("Lagos, Nigeria or
    Nairobi, Kenya", "Remote locations: Ghana, Kenya, …") gets no city, and a country only when
    every place named is in that same country.
    """
    if not location:
        return None, None, None
    text = _WORK_MODE_PREFIX.sub("", location).strip(" .,;:-–")
    if not text or _UNBOUNDED.search(text):
        return None, None, None
    groups = [g.strip(" .,") for g in _ALTERNATIVES.split(text) if g and g.strip(" .,")]
    if len(groups) > 1:
        # "Kano, Nigeria or Gombe, Nigeria" → Nigeria; any group naming no country or another one → none.
        group_countries = [match_country(g.split(",")[-1]) for g in groups]
        same = group_countries[0] if all(c and c == group_countries[0] for c in group_countries) else None
        return None, None, same
    parts = [p.strip(" .") for p in text.split(",") if p.strip(" .")]
    if len({c for c in (match_country(p) for p in parts) if c}) > 1:  # "Kenya, Rwanda, Malawi"
        return None, None, None
    if "/" in parts[0]:  # "Goma/Bukavu/Kinshasa, DRC": several cities in one country
        parts = parts[1:] or parts
        city_known = False
    else:
        city_known = True
    country = match_country(parts[-1]) if parts else None
    if country:
        places = parts[:-1]
        city = places[0] if places and city_known else None
        region = places[1] if len(places) >= 2 else None
        return city, region, country
    if len(parts) >= 3:
        return parts[0], parts[1], None
    if len(parts) == 2:
        # "Austin, TX": a two-letter code is a region; anything unrecognized isn't stored as a country.
        return parts[0], parts[1] if len(parts[1]) == 2 and parts[1].isupper() else None, None
    return None, None, None
