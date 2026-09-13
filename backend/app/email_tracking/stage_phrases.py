"""Phrase dictionaries for the deterministic recruitment-stage classifier (spec §20-23).

Config-driven on purpose (spec §22: "Phrase lists must be configuration/data driven") — adding or
tuning a phrase never requires touching classifier logic, only this file. Every phrase is matched
case-insensitively against normalized (whitespace-collapsed, lowercased) subject+body text.

Stage keys are `app.models.application.ApplicationStage` values directly — the classifier's output
is fed straight into the existing Phase 5 stage-transition endpoint with no translation layer.
"""

STAGE_PHRASES: dict[str, list[str]] = {
    "APPLICATION_RECEIVED": [
        "thank you for applying",
        "application received",
        "we have received your application",
        "application confirmation",
        "your application has been submitted",
    ],
    "UNDER_REVIEW": [
        "your application is under review",
        "currently reviewing your application",
        "reviewing applications",
    ],
    "SHORTLISTED": [
        "you have been shortlisted",
        "you've been shortlisted",
        "selected to proceed",
        "progressed to the next stage",
        "pleased to inform you that you have progressed",
        "we are pleased to inform you that you have been shortlisted",
    ],
    "APTITUDE_TEST": [
        "complete an online assessment",
        "assessment invitation",
        "aptitude test",
        "assessment deadline",
        "invited to complete an assessment",
        "invited to complete an online assessment",
        "online assessment invitation",
    ],
    "ASSESSMENT_COMPLETED": [
        "thank you for completing the assessment",
        "we have received your assessment results",
        "your assessment has been completed",
    ],
    "RECRUITER_SCREEN": [
        "recruiter call",
        "phone screen",
        "screening call",
        "initial conversation",
        "introductory call",
    ],
    "INTERVIEW": [
        "invite you to interview",
        "interview invitation",
        "schedule your interview",
        "interview availability",
        "would like to invite you for an interview",
    ],
    "FINAL_INTERVIEW": [
        "final interview",
        "final-stage interview",
        "next and final interview",
        "final round",
    ],
    "ASSESSMENT_CENTRE": [
        "assessment centre",
        "assessment center",
        "selection centre",
        "selection center",
    ],
    "BACKGROUND_CHECK": [
        "background check",
        "background verification",
        "reference check",
        "employment verification",
    ],
    "MEDICAL": [
        "pre-employment medical",
        "medical examination",
        "fitness assessment",
        "medical assessment",
    ],
    "OFFER": [
        "offer of employment",
        "employment offer",
        "pleased to offer you",
        "offer letter",
        "we are delighted to offer you",
    ],
    "REJECTED": [
        "regret to inform",
        "will not be progressing",
        "not moving forward",
        "unsuccessful application",
        "we have decided not to proceed",
        "on this occasion you have been unsuccessful",
    ],
}

# Recruitment-vocabulary signals used by the *pre-filter* (spec §19) to decide whether a message
# plausibly concerns recruitment at all, independent of which stage it might indicate. Deliberately
# broader than STAGE_PHRASES so a message can pass the pre-filter and still fail to match any
# specific stage (→ UNMATCHED rather than silently dropped).
GENERAL_RECRUITMENT_VOCABULARY: list[str] = [
    "application",
    "candidate",
    "recruitment",
    "recruiter",
    "hiring",
    "position",
    "role",
    "vacancy",
    "career",
    "job opening",
    "talent acquisition",
    "hr team",
    "human resources",
]

# Phrases that describe recruitment in general/aggregate terms rather than making a direct
# statement about the recipient — spec §23's critical negative-context rule. A message containing
# one of these (and nothing more specific/personal) must NOT be treated as evidence of personal
# progression, even though it contains stage-sounding vocabulary.
NEGATIVE_CONTEXT_PATTERNS: list[str] = [
    "only shortlisted candidates will be contacted",
    "only successful candidates will be contacted",
    "shortlisted candidates may be invited",
    "shortlisted candidates will be invited",
    "if you are shortlisted",
    "if shortlisted",
    "candidates will be contacted",
    "due to the high volume of applications",
    "we receive a high volume of applications",
    "unfortunately we cannot respond to every applicant",
]

# First/second-person, recipient-directed phrasing (spec §26 "recipient-directed language") that
# strengthens confidence a stage phrase is actually about *this* candidate, not recruitment in
# general.
RECIPIENT_DIRECTED_MARKERS: list[str] = [
    "you have been",
    "you've been",
    "your application",
    "your interview",
    "your assessment",
    "we would like to invite you",
    "we are pleased to",
    "we are delighted to",
    "congratulations",
    "dear ",
]
