# CareerOS — Privacy

## Sensitive data categories

CVs, cover letters, certificates, transcripts, reference letters, connected-email metadata, application
records, interview audio recordings, and full profile data are all treated as sensitive. None of it is
ever sent to a third-party AI API — scoring/matching/classification are local, deterministic engines
(`ARCHITECTURE.md` → Scoring engines), by design and by spec Rule 8/9.

## Document storage

- Documents are stored with per-user access control; a document's storage key is never guessable and
  is served only via a short-lived signed URL issued to the owning user's authenticated session.
  No document is ever publicly listable or accessible without authentication.
- Uploads are validated by content-type and size before storage (see `API.md` → `/documents`, and
  spec §74 Image Handling for images specifically).

## Email integration (Gmail/Outlook) — opt-in only

- Manual application tracking is fully functional with **no** email connection at all; connecting
  email is an enhancement, never a requirement.
- OAuth scope requested is the minimum needed to read recruitment-relevant messages (read-only mail
  scope), never full mailbox management/send scopes.
- The classifier extracts only what it needs to match a message to an application (sender domain,
  subject/body keywords, detected stage, confidence score) — it does not ingest or retain the full
  body of unrelated mail.
- **No automatic stage change is ever applied.** Every detected update is surfaced to the user as a
  confirmation card (`Confirm Update` / `Wrong Application` / `Ignore`); only a user action writes to
  `application_stage_events`.
- Settings expose `Disconnect Gmail`, `Disconnect Outlook`, and `Delete imported recruitment metadata`
  as first-class actions, not buried preferences.

## Account deletion

Deleting an account removes profile data, documents, and application history; it is a real delete
path (see `DATABASE.md` soft-delete conventions — account deletion is one of the explicit hard-delete
exceptions), not a soft "deactivate" that leaves data recoverable indefinitely.

## Language discipline (spec §9/§20/§18/§9)

- Scholarship eligibility is always shown as a partial match with ✓/△/✕ per criterion — never as an
  unconditional "you are eligible."
- Company intelligence "why this matters" copy uses hedged language ("may increase relevance of...",
  "could affect demand for...") — it never states that a news item guarantees hiring.
- Skill proficiency levels are user-declared (Beginner/Intermediate/Advanced/Expert) unless a real
  assessment produced a score; no fabricated percentages.

## Demo/seed data

All seed content (jobs, scholarships, companies, questions, applications, news) used in development is
clearly flagged in the database (`is_demo` style flag, to be added with the relevant migration) and
must never be presented to a production user as a real, current vacancy or opportunity.
