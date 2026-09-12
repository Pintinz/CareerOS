"""Maps a job's title/field/industry to relevant Technical-section topic slugs (spec §11/§15).

Pure keyword lookup — no AI. Each entry is a set of keywords; if any keyword appears (case-
insensitive substring match) in the job's title, field, or industry, that entry's topics are
added to the priority set for question selection. Extensible: add an entry, no code change
needed elsewhere.
"""

TECHNICAL_TOPIC_MAP: list[tuple[set[str], list[str]]] = [
    (
        {"process technician", "process operator", "refinery", "oil & gas", "oil and gas", "petrochemical"},
        [
            "pumps", "valves", "compressors", "p-and-ids", "dcs", "scada", "instrumentation",
            "process-safety", "flow", "pressure", "temperature", "heat-exchangers", "separators",
            "loto", "troubleshooting", "fluid-mechanics", "thermodynamics",
        ],
    ),
    (
        {"mechanical engineer", "mechanical engineering", "manufacturing", "maintenance"},
        [
            "pumps", "valves", "compressors", "fluid-mechanics", "thermodynamics", "troubleshooting",
            "preventive-maintenance", "heat-exchangers",
        ],
    ),
    (
        {"electrical engineer", "electrical engineering", "instrumentation engineer"},
        ["instrumentation", "scada", "dcs", "electrical-safety", "loto"],
    ),
    (
        {"data analyst", "data analytics", "data science", "business intelligence"},
        ["sql", "excel", "statistics", "data-interpretation", "visualization", "probability"],
    ),
    (
        {"machine learning", "ml engineer", "ai engineer"},
        ["statistics", "probability", "python", "algorithms", "data-interpretation"],
    ),
    (
        {"software engineer", "software developer", "backend engineer", "frontend engineer"},
        ["algorithms", "data-structures", "databases", "system-design", "debugging"],
    ),
    (
        {"cybersecurity", "security analyst", "infosec"},
        ["network-security", "threat-detection", "encryption", "incident-response"],
    ),
    (
        {"finance", "financial analyst", "accounting", "accountant"},
        ["financial-statements", "ratios", "budgeting", "auditing", "taxation"],
    ),
    (
        {"business", "operations", "management"},
        ["process-improvement", "kpis", "project-management", "stakeholder-management"],
    ),
]


def topics_for(*, field: str | None, industry: str | None, job_role: str | None) -> list[str]:
    haystack = " ".join(filter(None, [field, industry, job_role])).lower()
    if not haystack.strip():
        return []

    matched: list[str] = []
    for keywords, topics in TECHNICAL_TOPIC_MAP:
        if any(keyword in haystack for keyword in keywords):
            matched.extend(t for t in topics if t not in matched)
    return matched
