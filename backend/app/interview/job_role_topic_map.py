"""Maps a job's title/field/industry to relevant interview topic slugs (spec §10) — pure keyword
lookup, no AI. Deliberately separate from `app.aptitude.technical_topic_map`: interview prep needs
process/behavioral topics (shift handover, emergency response) that have no aptitude-question
equivalent, so the two engines are related in spirit but not coupled in code.

Each entry maps a set of keywords to a list of interview topic slugs; if any keyword appears
(case-insensitive substring) in the job's title, field, or industry, that entry's topics are added
to the priority set for question selection. Extensible: add an entry, no code change needed
elsewhere.
"""

JOB_ROLE_INTERVIEW_TOPIC_MAP: list[tuple[set[str], list[str]]] = [
    (
        {"process technician", "process operator", "refinery", "oil & gas", "oil and gas", "petrochemical"},
        [
            "process-monitoring", "pumps", "valves", "dcs", "scada", "loto", "p-and-ids",
            "process-safety", "troubleshooting", "abnormal-conditions", "shift-handover",
            "emergency-response",
        ],
    ),
    (
        {"mechanical engineer", "mechanical engineering", "manufacturing", "maintenance"},
        [
            "pumps", "valves", "troubleshooting", "preventive-maintenance", "process-safety",
            "quality-control", "root-cause-analysis",
        ],
    ),
    (
        {"electrical engineer", "electrical engineering", "instrumentation engineer"},
        ["instrumentation", "scada", "dcs", "electrical-safety", "loto", "troubleshooting"],
    ),
    (
        {"data analyst", "data analytics", "data science", "business intelligence"},
        ["data-storytelling", "sql-scenarios", "stakeholder-communication", "data-quality", "experimentation"],
    ),
    (
        {"machine learning", "ml engineer", "ai engineer"},
        ["model-evaluation", "data-pipelines", "experimentation", "production-ml", "ethics-and-bias"],
    ),
    (
        {"software engineer", "software developer", "backend engineer", "frontend engineer"},
        ["system-design", "debugging-scenarios", "code-quality", "collaboration", "incident-response"],
    ),
    (
        {"cybersecurity", "security analyst", "infosec"},
        ["incident-response", "threat-detection", "risk-assessment", "compliance"],
    ),
    (
        {"finance", "financial analyst", "accounting", "accountant"},
        ["financial-analysis", "reporting-accuracy", "regulatory-compliance", "stakeholder-communication"],
    ),
    (
        {"sales", "account executive", "business development"},
        ["prospecting", "objection-handling", "negotiation", "relationship-management"],
    ),
    (
        {"marketing", "brand", "growth"},
        ["campaign-strategy", "data-driven-decisions", "stakeholder-communication", "brand-consistency"],
    ),
    (
        {"human resources", "hr generalist", "recruiter", "talent acquisition"},
        ["conflict-resolution", "confidentiality", "employee-relations", "compliance"],
    ),
    (
        {"operations", "operations manager", "supply chain"},
        ["process-improvement", "kpis", "vendor-management", "root-cause-analysis"],
    ),
    (
        {"management", "team lead", "supervisor", "manager"},
        ["team-leadership", "performance-management", "conflict-resolution", "delegation", "decision-making"],
    ),
]


def topics_for(*, field: str | None, industry: str | None, job_role: str | None) -> list[str]:
    haystack = " ".join(filter(None, [field, industry, job_role])).lower()
    if not haystack.strip():
        return []

    matched: list[str] = []
    for keywords, topics in JOB_ROLE_INTERVIEW_TOPIC_MAP:
        if any(keyword in haystack for keyword in keywords):
            matched.extend(t for t in topics if t not in matched)
    return matched
