"""Static defaults for the company-research checklist (spec §26) and the curated "questions to
ask the interviewer" catalog (spec §27). Both are editorial content, not admin-manageable tables
yet — extensible Python data, matching the seed-data-first pattern used elsewhere in this project."""

DEFAULT_CHECKLIST_ITEMS: list[tuple[str, str]] = [
    ("understand_business", "Understand the company's business"),
    ("review_developments", "Review the latest company developments"),
    ("understand_role", "Understand the role"),
    ("review_technical_requirements", "Review technical requirements"),
    ("prepare_star_stories", "Prepare 5 STAR stories"),
    ("review_safety_expectations", "Review safety expectations"),
    ("prepare_questions_to_ask", "Prepare questions to ask the interviewer"),
]

# Checklist items counted toward the "Company Preparation" readiness component (spec §11) — the
# rest are general/role/STAR prep, already reflected in their own components.
COMPANY_PREP_CHECKLIST_KEYS = {"understand_business", "review_developments"}


def default_checklist() -> dict[str, bool]:
    return {key: False for key, _ in DEFAULT_CHECKLIST_ITEMS}


# (id, text, category) — categories per spec §27.
QUESTIONS_TO_ASK_CATALOG: list[tuple[str, str, str]] = [
    ("role-1", "What does a typical day look like in this role?", "Role"),
    ("role-2", "What are the most important priorities for this role in the first 90 days?", "Role"),
    ("team-1", "Can you tell me about the team I'd be working with?", "Team"),
    ("team-2", "How does this team collaborate with other departments?", "Team"),
    ("performance-1", "How is success measured for this role?", "Performance"),
    ("performance-2", "What does the performance review process look like?", "Performance"),
    ("training-1", "What onboarding or training is provided for new hires?", "Training"),
    ("training-2", "Are there opportunities for professional development or certifications?", "Training"),
    ("technology-1", "What tools, systems, or technologies does the team use day to day?", "Technology"),
    ("technology-2", "Are there any planned changes to the technology or processes I should know about?", "Technology"),
    ("culture-1", "How would you describe the team culture?", "Culture"),
    ("culture-2", "What do people enjoy most about working here?", "Culture"),
    ("career-1", "What does career progression typically look like from this role?", "Career Growth"),
    ("career-2", "Are there opportunities to grow into other areas of the business?", "Career Growth"),
    ("safety-1", "What safety protocols and training are in place for this role?", "Safety"),
    ("safety-2", "How does the company handle near-miss or incident reporting?", "Safety"),
    ("operations-1", "What are the biggest operational challenges the team is currently facing?", "Operations"),
    ("operations-2", "How does this role support the company's broader operational goals?", "Operations"),
]
