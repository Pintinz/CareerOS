"""Weighted application-matching engine (spec §24-25). Pure functions over plain dataclasses — no
database access here, so it's fully unit-testable and every weight lives in
`matching_config.MATCH_WEIGHTS` rather than being scattered through this file.
"""

from datetime import timedelta

from app.email_tracking.matching_config import MATCH_AMBIGUITY_MARGIN, MATCH_MIN_SCORE, MATCH_WEIGHT_TOTAL, MATCH_WEIGHTS
from app.email_tracking.text_utils import as_aware_utc, company_slug, extract_reference_tokens, normalize, word_overlap_ratio
from app.email_tracking.types import ApplicationSignal, MatchCandidate, MatchResult, RawEmail

_TIMING_WINDOW_DAYS = 180


def _score_application(email: RawEmail, sender_domain: str, app: ApplicationSignal) -> MatchCandidate:
    text = normalize(f"{email.subject} {email.body_text}")
    email_tokens = extract_reference_tokens(text)
    evidence: list[str] = []
    signals: set[str] = set()
    points = 0.0

    # job_or_reference_id: any reference-looking token from the email also appears in the
    # application's job posting URL (job boards commonly embed the requisition id in the URL).
    job_url_tokens = extract_reference_tokens(app.job_url or "")
    if email_tokens & job_url_tokens:
        points += MATCH_WEIGHTS["job_or_reference_id"]
        evidence.append("Job/reference ID matched")
        signals.add("application_identifier_match")

    # reference_id: a token appears near an explicit "reference"/"ref"/"application id" label.
    for label in ("reference", "ref:", "ref ", "application id", "req id", "job id"):
        idx = text.find(label)
        if idx == -1:
            continue
        window = text[idx : idx + len(label) + 20]
        if extract_reference_tokens(window) & job_url_tokens:
            points += MATCH_WEIGHTS["reference_id"]
            evidence.append("Explicit reference/application ID label matched")
            signals.add("application_identifier_match")
            break

    # company_domain: sender domain contains the company's slug, or the company name/slug appears
    # directly in the subject/body text.
    slug = company_slug(app.company_name)
    if slug and (slug in sender_domain.replace(".", "") or slug in text.replace(" ", "")):
        points += MATCH_WEIGHTS["company_domain"]
        evidence.append(f"Company '{app.company_name}' matched")
        signals.add("company_match")

    # job_title: word-overlap between the tracked role title and the email text.
    title_overlap = word_overlap_ratio(app.role_title, text)
    if title_overlap >= 0.6:
        points += MATCH_WEIGHTS["job_title"]
        evidence.append(f"Role title '{app.role_title}' matched")
        signals.add("role_match")
    elif title_overlap >= 0.3:
        points += MATCH_WEIGHTS["job_title"] * 0.5
        evidence.append(f"Role title '{app.role_title}' partially matched")
        signals.add("role_match")

    # timing: the email arrived within a plausible window after the application was submitted.
    if app.applied_date is not None:
        delta = as_aware_utc(email.received_at) - as_aware_utc(app.applied_date)
        if timedelta(0) <= delta <= timedelta(days=_TIMING_WINDOW_DAYS):
            points += MATCH_WEIGHTS["timing"]
            evidence.append("Timing consistent with this application")
            signals.add("timing_context")

    # location: a location token for this application appears in the email text.
    if app.location and normalize(app.location) in text:
        points += MATCH_WEIGHTS["location"]
        evidence.append(f"Location '{app.location}' matched")

    return MatchCandidate(
        application_id=app.application_id,
        score=points / MATCH_WEIGHT_TOTAL,
        evidence=evidence,
        signals=frozenset(signals),
    )


def match_application(email: RawEmail, sender_domain: str, applications: list[ApplicationSignal]) -> MatchResult:
    """Never guesses: returns "matched" only when exactly one application clears the minimum score
    and beats every other candidate by more than the ambiguity margin; "ambiguous" when two or more
    candidates are too close to call; "unmatched" when nothing clears the bar at all (spec §25)."""
    if not applications:
        return MatchResult(status="unmatched", matched_id=None, candidate_ids=[], evidence=[])

    scored = [_score_application(email, sender_domain, app) for app in applications]
    qualifying = sorted((c for c in scored if c.score >= MATCH_MIN_SCORE), key=lambda c: c.score, reverse=True)

    if not qualifying:
        return MatchResult(status="unmatched", matched_id=None, candidate_ids=[], evidence=[])

    top = qualifying[0]
    close_rivals = [c for c in qualifying[1:] if (top.score - c.score) <= MATCH_AMBIGUITY_MARGIN]
    if close_rivals:
        candidate_ids = [top.application_id] + [c.application_id for c in close_rivals]
        return MatchResult(status="ambiguous", matched_id=None, candidate_ids=candidate_ids, evidence=top.evidence)

    return MatchResult(
        status="matched", matched_id=top.application_id, candidate_ids=[], evidence=top.evidence, signals=top.signals
    )
