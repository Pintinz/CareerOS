"""Deterministic text helpers for ingestion: HTML → plain text, list extraction, dates, hashing.

Everything a source returns is untrusted. HTML is never stored or rendered as HTML: it is parsed
(no network, no entity expansion beyond HTML's own), scripts/styles are dropped, and only visible
text survives, bounded in length.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from lxml import html as lxml_html
from lxml.etree import ParserError

_WS = re.compile(r"[ \t\f\v ]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_DROP_TAGS = ("script", "style", "noscript", "template", "iframe", "object", "embed", "svg", "form", "button", "head")
_BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "blockquote"}
MAX_HTML_INPUT_CHARS = 2_000_000


def clean_text(value: str | None, *, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value))
    text = _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(_WS.sub(" ", line).strip() for line in text.split("\n"))
    text = _BLANK_LINES.sub("\n\n", text).strip()
    if max_length is not None and len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "…"
    return text or None


def _parse_fragment(markup: str):
    markup = markup[:MAX_HTML_INPUT_CHARS]
    if "<" not in markup:
        return None
    try:
        root = lxml_html.fromstring(f"<div>{markup}</div>")
    except (ParserError, ValueError):
        return None
    for tag in _DROP_TAGS:
        for element in root.findall(f".//{tag}"):
            element.drop_tree()
    return root


def html_to_text(markup: str | None, *, max_length: int | None = 20_000) -> str | None:
    if not markup:
        return None
    # Greenhouse returns entity-escaped HTML ("&lt;p&gt;"); unescape once before parsing.
    if "&lt;" in markup and "<" not in markup:
        markup = html.unescape(markup)
    root = _parse_fragment(markup)
    if root is None:
        return clean_text(html.unescape(markup), max_length=max_length)
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if element.tag in _BLOCK_TAGS:
            element.tail = "\n" + (element.tail or "")
            if element.tag == "li":
                element.text = "• " + (element.text or "")
    return clean_text(root.text_content(), max_length=max_length)


def html_list_items(markup: str | None, *, max_items: int = 40, max_item_length: int = 500) -> list[str]:
    if not markup:
        return []
    if "&lt;" in markup and "<" not in markup:
        markup = html.unescape(markup)
    root = _parse_fragment(markup)
    if root is None:
        return []
    items = []
    for li in root.iter("li"):
        text = clean_text(li.text_content(), max_length=max_item_length)
        if text:
            items.append(text)
        if len(items) >= max_items:
            break
    return items


def text_lines_as_list(text: str | None, *, max_items: int = 40, max_item_length: int = 500) -> list[str]:
    if not text:
        return []
    items = []
    for line in text.split("\n"):
        line = clean_text(line.lstrip("•-*·▪◦ "), max_length=max_item_length)
        if line:
            items.append(line)
        if len(items) >= max_items:
            break
    return items


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKC", title).lower()
    text = re.sub(r"[\(\)\[\]{}|/\\,.;:!?\"'’“”–—-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    text = normalize_title(name)
    text = re.sub(r"\b(plc|ltd|limited|inc|incorporated|llc|gmbh|ag|sa|nv|bv|co|company|corp|corporation|group|holdings)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip() or None


def parse_datetime(value) -> datetime | None:
    """ISO-8601, RFC-822 (RSS), epoch seconds/milliseconds, or date-only. Always timezone-aware
    UTC. Returns None rather than guessing on anything else."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return parse_datetime(int(text))
    iso = text.replace("Z", "+00:00") if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(iso)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def content_hash(*parts) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(repr(part).encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()


def title_similarity(a: str, b: str) -> float:
    """Token-set similarity in [0, 1] — robust to word order and small additions ("Senior")."""
    ta, tb = set(normalize_title(a).split()), set(normalize_title(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
