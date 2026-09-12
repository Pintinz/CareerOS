"""Keyword synonym normalization (spec §15 example: PLC <-> Programmable Logic Controller).

Small, explicit, extensible groups — each group of phrases is treated as the same concept for
matching purposes. This is a lookup table, not a language model; add entries as real CVs/JDs
surface more industry jargon pairs worth normalizing.
"""

SYNONYM_GROUPS: list[list[str]] = [
    ["plc", "programmable logic controller"],
    ["preventive maintenance", "planned maintenance"],
    ["hse", "health safety environment", "health, safety and environment"],
    ["dcs", "distributed control system"],
    ["scada", "supervisory control and data acquisition"],
    ["p&id", "piping and instrumentation diagram", "piping and instrumentation diagrams"],
    ["loto", "lockout tagout", "lockout/tagout"],
    ["hvac", "heating ventilation and air conditioning"],
    ["qa", "quality assurance"],
    ["qc", "quality control"],
    ["ci/cd", "continuous integration and continuous deployment", "continuous integration/continuous deployment"],
    ["api", "application programming interface"],
    ["ui", "user interface"],
    ["ux", "user experience"],
    ["db", "database"],
    ["ml", "machine learning"],
    ["ai", "artificial intelligence"],
    ["kpi", "key performance indicator", "key performance indicators"],
    ["sop", "standard operating procedure", "standard operating procedures"],
]

_CANONICAL_BY_PHRASE: dict[str, str] = {}
for group in SYNONYM_GROUPS:
    canonical = group[0]
    for phrase in group:
        _CANONICAL_BY_PHRASE[phrase] = canonical


def canonicalize(phrase: str) -> str:
    """Maps a lowercased phrase to its canonical form if it's a known synonym, else returns it
    unchanged."""
    return _CANONICAL_BY_PHRASE.get(phrase, phrase)


def normalize_text_for_matching(text: str) -> str:
    """Replaces every known synonym phrase in `text` (already lowercased) with its canonical
    form, longest phrases first so multi-word synonyms aren't shadowed by shorter substrings."""
    normalized = text
    for phrase in sorted(_CANONICAL_BY_PHRASE, key=len, reverse=True):
        canonical = _CANONICAL_BY_PHRASE[phrase]
        if phrase != canonical:
            normalized = normalized.replace(phrase, canonical)
    return normalized
