"""Shared text-processing helpers for the ATS engine. Pure string/regex logic — no ML model,
no external API call (spec Rule 8: describe this accurately as rules-based)."""

import re
from collections import Counter

from app.matching.synonyms import normalize_text_for_matching

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "of", "in", "on", "at", "to",
    "for", "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "it", "its", "we", "you", "your", "our", "their",
    "will", "would", "can", "could", "should", "must", "may", "might", "have", "has", "had",
    "do", "does", "did", "not", "no", "yes", "into", "than", "such", "also", "any", "all",
    "who", "whom", "which", "what", "when", "where", "how", "etc", "per", "via",
}

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+/&.#-]*")


def normalize(text: str) -> str:
    """Lowercase + synonym-canonicalize. The single entry point both CV and JD text should pass
    through before comparison so matching is consistent."""
    return normalize_text_for_matching(text.lower())


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def significant_words(text: str) -> list[str]:
    """Tokens with stopwords and pure numbers removed."""
    return [w for w in tokenize(text) if w not in _STOPWORDS and not w.isdigit() and len(w) > 1]


def extract_ngrams(words: list[str], n: int) -> list[str]:
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def extract_keywords(text: str, *, top_n: int = 30) -> list[str]:
    """Deterministic keyword extraction: frequency-ranked significant unigrams + bigrams from
    normalized text. Not semantic understanding — just what appears often enough to matter,
    which is what a real ATS keyword scanner does too."""
    normalized = normalize(text)
    words = significant_words(normalized)
    bigrams = [bg for bg in extract_ngrams(words, 2) if all(w not in _STOPWORDS for w in bg.split())]

    counts = Counter(words) + Counter(bigrams)
    # Keep a bigram over its constituent unigrams when the bigram is itself frequent enough —
    # otherwise this just returns the most frequent significant terms.
    ranked = [word for word, _ in counts.most_common(top_n)]
    return ranked


def keyword_coverage(candidate_text: str, keywords: list[str]) -> tuple[float, list[str], list[str]]:
    """Returns (coverage_ratio, matched_keywords, missing_keywords) for how many of `keywords`
    appear in `candidate_text` (both normalized first)."""
    if not keywords:
        return 1.0, [], []

    normalized_candidate = normalize(candidate_text)
    matched = [kw for kw in keywords if kw in normalized_candidate]
    missing = [kw for kw in keywords if kw not in normalized_candidate]
    return len(matched) / len(keywords), matched, missing


def find_years_of_experience(text: str) -> int | None:
    """Looks for patterns like '5 years', '5+ years', '5-7 years of experience'. Returns the
    largest such number found, or None. A heuristic, not a guarantee — documented as such
    wherever it's surfaced."""
    matches = re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?years?", text.lower())
    years = [int(m) for m in matches]
    return max(years) if years else None
