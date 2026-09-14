"""Prompt-injection resistance and evidence checks for the research layer (spec §17, §35).

Public web pages are untrusted input. Defence in depth, none of which relies on the model
"behaving":

1. Framing — page text is wrapped in an unguessable per-request boundary and described to the
   model as data; any occurrence of the boundary tag inside the page is removed first.
2. No authority to act — the structured output schema has no field that could express publishing,
   approval, verification or status; the pipeline sets queue status itself, always.
3. Marker scan — instruction-like text in a page is detected independently of the model and
   flagged to admins; flagged items get capped confidence and can never be auto-published.
4. Evidence checks — every extracted title, deadline, quote and URL is checked against the page
   the backend itself fetched. Unsupported facts are dropped, not trusted.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field

from app.ingestion.text import normalize_title
from app.ingestion.url_safety import is_ats_url, registrable_domain

BOUNDARY_TAG = "untrusted_page_content"
MAX_RESEARCH_PAGE_CHARS = 60_000

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier|preceding)\s+(instructions|prompts|rules|messages)",
    r"disregard\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|system)\s+",
    r"forget\s+(all\s+|your\s+)?(previous\s+)?instructions",
    r"\b(system|developer)\s+prompt\b",
    r"you\s+are\s+now\s+",
    r"\bact\s+as\s+(an?\s+)?(ai|assistant|admin|administrator)",
    r"\b(publish|approve|auto-?publish)\s+(this|the)\s+(job|listing|post|item|opportunity|scholarship)",
    r"\bmark\s+(this|it)\s+(as\s+)?(verified|approved|official)",
    r"\bset\s+(the\s+)?(status|confidence|trust)\s+(to|=)",
    r"<\|?(im_start|im_end|system|endoftext)\|?>",
    r"\[\s*(system|inst)\s*\]",
    r"^\s*(system|assistant)\s*:",
    r"\bjailbreak\b|\bdeveloper\s+mode\b",
    r"\bnew\s+instructions\s*:",
    r"\bdo\s+not\s+(tell|inform)\s+(the\s+)?(user|admin|editor)",
]
_INJECTION = re.compile("|".join(f"(?:{p})" for p in _INJECTION_PATTERNS), re.IGNORECASE | re.MULTILINE)


def detect_injection_markers(text: str | None) -> list[str]:
    """Up to five short, normalized snippets of instruction-like page text (for admin evidence)."""
    if not text:
        return []
    found = []
    for match in _INJECTION.finditer(text):
        snippet = re.sub(r"\s+", " ", match.group(0)).strip()[:80]
        if snippet.lower() not in (s.lower() for s in found):
            found.append(snippet)
        if len(found) >= 5:
            break
    return found


@dataclass
class FramedPage:
    boundary: str
    content: str
    truncated: bool


def frame_untrusted_page(text: str) -> FramedPage:
    boundary = secrets.token_hex(12)
    cleaned = re.sub(rf"</?\s*{BOUNDARY_TAG}[^>]*>", " ", text, flags=re.IGNORECASE)
    truncated = len(cleaned) > MAX_RESEARCH_PAGE_CHARS
    if truncated:
        cleaned = cleaned[:MAX_RESEARCH_PAGE_CHARS]
    return FramedPage(
        boundary=boundary,
        content=f'<{BOUNDARY_TAG} boundary="{boundary}">\n{cleaned}\n</{BOUNDARY_TAG} boundary="{boundary}">',
        truncated=truncated,
    )


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_title(text)).strip()


def title_supported(title: str, page_text: str, *, threshold: float = 0.6) -> bool:
    tokens = [t for t in _norm(title).split() if len(t) > 1]
    if not tokens:
        return False
    page_tokens = set(_norm(page_text).split())
    return sum(1 for t in tokens if t in page_tokens) / len(tokens) >= threshold


def quote_supported(quote: str, page_text: str) -> bool:
    q = _norm(quote)
    return bool(q) and q in _norm(page_text)


_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def date_supported(value, page_text: str) -> bool:
    """A date is supported when its year appears and either its month name/abbreviation or a
    numeric day-month form appears near it on the page."""
    if value is None:
        return True
    text = page_text.lower()
    if str(value.year) not in text:
        return False
    month = _MONTHS[value.month - 1]
    numeric = [f"{value.day}/{value.month}", f"{value.month}/{value.day}", f"{value.day:02d}/{value.month:02d}",
               f"{value.month:02d}/{value.day:02d}", f"{value.year}-{value.month:02d}", f"{value.day}.{value.month}."]
    return month in text or month[:3] in text or any(n in text for n in numeric)


def url_allowed(url: str | None, *, source_url: str, page_url: str) -> bool:
    if not url:
        return True
    domain = registrable_domain(url)
    return domain is not None and (domain in {registrable_domain(source_url), registrable_domain(page_url)} or is_ats_url(url))


@dataclass
class EvidenceReport:
    passed: bool = True
    flags: list[str] = field(default_factory=list)
    dropped_fields: list[str] = field(default_factory=list)
    injection_markers: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "flags": self.flags,
            "dropped_fields": self.dropped_fields,
            "injection_suspected": bool(self.injection_markers),
            "injection_markers": self.injection_markers,
        }


INJECTION_CONFIDENCE_CAP = 0.4
AI_CONFIDENCE_CAP = 0.75
