"""Known ATS/recruitment-platform sender domains (spec §19) — used only as one *signal* feeding the
recruitment pre-filter and confidence model, never as sole proof of a stage change and never trusted
purely from a sender *display name* (spec §19's explicit warning). A message from
`no-reply@myworkday.com` is more likely to be genuine recruitment mail than one from a random
free-mail address, but it still has to pass phrase/negative-context/matching checks like anything
else.

Configuration-driven so new ATS platforms can be added without touching classifier logic.
"""

KNOWN_ATS_DOMAINS: list[str] = [
    "myworkday.com",
    "workday.com",
    "greenhouse.io",
    "lever.co",
    "hire.lever.co",
    "ashbyhq.com",
    "smartrecruiters.com",
    "successfactors.com",
    "successfactors.eu",
    "oraclecloud.com",  # Oracle Recruiting Cloud tenants.
    "icims.com",
    "taleo.net",
    "bamboohr.com",
    "jobvite.com",
    "recruitee.com",
    "breezy.hr",
]


def is_known_ats_domain(domain: str) -> bool:
    domain = domain.lower()
    return any(domain == known or domain.endswith(f".{known}") for known in KNOWN_ATS_DOMAINS)
