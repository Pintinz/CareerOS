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
- **CVs specifically** (`cv_documents` table, Phase 3 ATS): the uploaded file's binary is never
  persisted — only the plain text extracted from it server-side (`app/services/document_extraction.py`)
  and never sent anywhere outside this backend. `GET /ats/cv` and `POST /ats/analyze` both require the
  owning user's bearer token; there is no route that returns another user's CV text or analysis
  history. A real document vault for the original files is a later phase — see `DATABASE.md`.

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

## Aptitude assessment data (Phase 6)

- A test session's questions/options/answers are visible only to the user who owns the session — every
  aptitude endpoint 404s (never 403) on a session that isn't the caller's, so existence isn't leaked
  either (same isolation pattern as `applications`).
- Correct answers (`is_correct` on an option) are **never** sent to the mobile client while a session is
  in progress — only after submission, via the dedicated review endpoint. There is no route that
  returns an answer key for an unsubmitted session, by construction of the response schemas
  (`SessionQuestionOut`/`OptionOut` simply have no `is_correct` field at all).
- Practicing an aptitude test **never** changes a linked application's real `current_stage` or its
  `assessment_completed` state — CareerOS practice is explicitly not the employer's official
  assessment, and the two are kept fully separate. Only the user's own `POST /applications/{id}/stage`
  call can move a real application forward.
- Locally cached exam data (see `ARCHITECTURE.md` → Mobile aptitude offline behavior) stays on-device
  in the app's own SharedPreferences store and is cleared once a session is submitted; it is never
  transmitted anywhere except back to this backend's own `/aptitude/*` endpoints.

## Interview preparation data (Phase 7)

- Session data, STAR stories, answers, and preparation progress are visible only to the owning
  user — every interview/STAR endpoint 404s (never 403) on a resource that isn't the caller's, same
  isolation pattern as aptitude/applications.
- **Audio recordings remain local by default.** `interview_answers.audio_path` stores a path to a
  file on the device only; the binary audio is **never automatically uploaded** to this backend or
  any third party. The mobile UI provides explicit Play/Rename/Delete controls, and recording only
  starts after the user explicitly grants microphone permission — nothing records automatically.
- **No external AI processing of interview answers.** Typed answers are checked only via the
  deterministic, local "Answer Structure Check" (word count, metric-presence, STAR-keyword hints —
  `app/interview/answer_check.py`); nothing is sent to an LLM or third-party analysis API.
- Self-assessment (`self_rating`, `used_star`, `gave_measurable_result`, `answered_exact_question`)
  is **entirely user-declared** — the backend stores exactly what the user selects and never
  infers, overrides, or reinterprets it as a system judgment. See PROJECT_STATUS.md for the full
  system-calculated vs. user-self-rated vs. editorially-tagged breakdown.
- Practicing interview questions (or completing a mock interview) **never** changes a linked
  application's real `current_stage` — identical guarantee to the aptitude engine, and verified by
  the same kind of test (`test_application_linked_session_resolves_job_and_does_not_mutate_stage`).
- Company tagging on interview questions (`interview_questions.company_id`) is **editorial
  metadata only** — it means "recommended practice for this company/role," never a claim that the
  question is a real, leaked interview question from that employer. Every company-preparation
  response carries an explicit disclaimer to this effect.
- Locally cached interview session data (see `ARCHITECTURE.md` → Mobile interview offline behavior)
  stays on-device in the app's own SharedPreferences store and is cleared once a session completes;
  it is never transmitted anywhere except back to this backend's own `/interview/*` endpoints.

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

All seed content used in development is clearly flagged in the database. `companies`, `jobs`, and
`scholarships` already carry an `is_demo` boolean column (see `scripts/seed_demo_data.py`); the same
convention applies to questions/applications/news once those tables exist. Demo content must never be
presented to a production user as a real, current vacancy or opportunity — the mobile/admin UI should
visibly badge `is_demo` records once real-vs-demo content coexists in the same environment.
