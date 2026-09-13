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
  spec §74 Image Handling for images specifically). Since Phase 7.5, every image upload through the
  shared pipeline (`POST /admin/uploads/image`) is also **actually decoded** with Pillow before being
  written to disk — content that merely claims to be an image via extension/Content-Type but doesn't
  decode is rejected (422), not stored. Storage keys are randomized (never derived from the
  client-supplied filename), defending against path traversal and filename collisions.
- **CVs specifically** (`cv_documents` table, Phase 3 ATS): the uploaded file's binary is never
  persisted — only the plain text extracted from it server-side (`app/services/document_extraction.py`)
  and never sent anywhere outside this backend. `GET /ats/cv` and `POST /ats/analyze` both require the
  owning user's bearer token; there is no route that returns another user's CV text or analysis
  history. A real document vault for the original files is a later phase — see `DATABASE.md`.

## Smart Recruitment Email Tracking (Gmail/Outlook/Forward-to-CareerOS — Phase 8, opt-in only)

**CareerOS is fully usable with zero email connection.** Manual application tracking (Phase 5) is
never degraded, hidden, or gated behind connecting a mailbox — Smart Application Tracking is
strictly an optional enhancement layered on top of it.

### Why mailbox access is requested

CareerOS asks for read-only mailbox access for one purpose only: to identify recruitment-related
messages and suggest updates to applications you're already tracking. It is never used to read your
mail for any other purpose, and never for advertising.

### What is requested (and what is deliberately *not* requested)

- **Gmail**: only the `gmail.readonly` OAuth scope. No `gmail.send`, `gmail.compose`,
  `gmail.modify`, or full mailbox-management scope is ever requested.
- **Outlook/Microsoft 365**: only delegated `Mail.Read` + `User.Read` + `offline_access`, scoped to
  the signed-in user's own mailbox. No `Mail.ReadWrite`/`Mail.Send`, and no tenant-wide application
  permission — CareerOS never asks an organization's admin to grant it broad access to every
  mailbox in a tenant.
- Both connections can be revoked by you at any time from Settings → Application Tracking, and
  disconnecting also stops CareerOS's own future processing (see Disconnect, below).

### What is processed (transiently) vs. what is retained

- The full email body is read transiently, in memory, to run the deterministic classifier — it is
  **never** written to CareerOS's database. This is not a shadow mailbox: CareerOS does not build,
  and cannot produce, a copy of your inbox.
- What *is* retained, per matched message (`recruitment_email_events` — see DATABASE.md): the
  provider's own message id (for deduplication), sender email/domain/name, subject line, received
  timestamp, which application (if any) it matched, the detected stage guess, the confidence score,
  a short (≤240 character) sanitized excerpt of *why* it matched (e.g. `"invited to complete an
  online assessment" was detected`), and the review status. No attachments are ever ingested.
- OAuth tokens are encrypted at rest (`TokenEncryptionService`, see ARCHITECTURE.md) and are never
  included in any API response, log line, or exception message.

### No automatic stage change — ever

This is the single non-negotiable rule of this entire feature: **CareerOS will never change an
application's stage without your explicit confirmation.** A detected update becomes a suggestion
you review on the "Recruitment Update Detected" screen (`Confirm Stage` / `Wrong Application` /
`Ignore` / `View Email Details`); only tapping `Confirm Stage` writes anything to
`application_stage_events`, and it does so by calling the exact same stage-transition endpoint a
manual update uses (`ApplicationService.update_stage`) — there is no separate, weaker code path.
Low-confidence detections don't even reach a push notification; they sit quietly under review status
rather than interrupting you.

### Explainability

Before confirming anything, you can always see *why* CareerOS suggested it — a short "Detected
because: • Company domain matched • Role title matched • '...phrase...' was detected" breakdown, not
a bare percentage. CareerOS never recreates a full email reader inside the app; only From/Subject/
Date/a short excerpt/the detection reasons are ever shown.

### Disconnect

Disconnecting a provider (Settings → Application Tracking → Disconnect): revokes CareerOS's access
on the provider's side where the provider supports it, stops the Gmail watch / deletes the Outlook
Graph subscription, clears CareerOS's own stored (encrypted) tokens, and marks the connection
disconnected so no further processing happens. It does **not** delete previously confirmed
application-stage history — that lives on the application itself, independent of any mailbox
connection, and is controlled separately (see below).

### Delete Recruitment Email Data

A separate "Delete Recruitment Email Data" control (Settings → Application Tracking) deletes every
stored `recruitment_email_events` row for your account — the metadata and suggestions described
above. It explicitly does **not** touch any already-confirmed application timeline entry; if you
want to undo a stage change you confirmed, edit the application itself.

### Forward Recruitment Email (the most private option)

Spec's fourth, privacy-friendly tracking method: forward any recruitment email yourself to a
personal, non-guessable CareerOS alias (`apply+<opaque-token>@...` — never a sequential or
otherwise-guessable identifier). This requires no account connection, no OAuth, and no standing
mailbox access at all. The alias and its data model exist; actually receiving and processing
forwarded mail requires an inbound-mail provider that is not configured in this environment, so this
method currently shows as unavailable rather than functioning end to end — see PROJECT_STATUS.md.

### What was NOT tested against a real provider

Everything above describes the real, implemented behavior — but it has only ever been exercised
against `MockEmailTrackingProvider` and hand-built webhook payloads in this environment, never a
genuine Gmail or Outlook account. See PROJECT_STATUS.md's Phase 8 completion report for the exact
implemented / mock-verified / blocked-by-credentials breakdown before treating any of this as
production-verified.

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
- **Audio recordings remain local by default (implemented Phase 7.5).** `interview_answers.audio_path`
  and the separate `interview_recordings` metadata table both store a path to a file **on the
  device only**; the binary audio is **never automatically uploaded** to this backend or any third
  party — `interview_recordings.upload_status` stays `"local_only"` because no upload code path
  exists at all, by design. The mobile session screen provides explicit Start/Stop/Play/Delete
  controls (a dedicated Rename control lives on the repository/API layer — `PUT
  /interview/recordings/{id}` — ready for the not-yet-built Recordings Manager screen; see
  PROJECT_STATUS.md). Recording only starts after the user explicitly taps "Start Recording" and
  grants microphone permission at that moment — **never at app startup**, and nothing records
  automatically. Before a user's first-ever recording attempt, the app shows a one-time notice —
  "Interview recordings are stored locally on this device unless you explicitly choose to upload or
  share them." with **Continue**/**Not Now** — and never repeats it once dismissed either way.
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

### Logging and webhook security

Structured logs for this feature may contain provider name, connection id, event id, processing
status, and error category — never an email body, OAuth access/refresh token, authorization code, or
full webhook payload. Webhook endpoints treat every inbound payload as untrusted: a Gmail Pub/Sub
notification for an address with no matching active connection is a quiet no-op, and Microsoft Graph
notification/lifecycle endpoints implement Graph's own required validation handshake before
accepting anything. Email content itself is never rendered as raw HTML in the app — only sanitized,
short plain-text excerpts are ever displayed.

## Admin visibility limits (Phase 9)

The admin CMS gives staff broad content-management power but deliberately narrow visibility into
user data:
- `GET /admin/users` and its response schema (`UserAdminOut`) never include `hashed_password`,
  OAuth access/refresh tokens, private CV text, email bodies/excerpts, interview recordings, or any
  `email_connections`/`recruitment_email_events` content — verified by a dedicated test
  (`test_user_admin_list_never_exposes_password_hash`).
- There is no admin inbox-viewer or raw-email reader anywhere in the product (spec §63) — the only
  email-tracking-related admin surface is the Operations dashboard's aggregate connection/health
  counts (never per-message content).
- Suspending or reactivating a user is restricted to ADMIN/SUPER_ADMIN roles and is logged to the
  append-only audit log (admin id, action, target user id, timestamp) — never silently invisible.
- `AuditLog.metadata` never contains secrets, tokens, or full user-generated content — only
  structural facts about what changed (entity type/id, action taken).
- System settings (`GET/PUT /admin/settings`) never expose API keys or other secrets — those remain
  in environment/secret management exclusively; only tunable scoring weights/thresholds live in the
  `system_settings` table.

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
- Interview readiness is a CareerOS product heuristic (six weighted, capped activity components —
  see ARCHITECTURE.md), **not** a scientifically validated predictor of real interview outcomes.
  Copy is phrased as "Interview Preparation Readiness: 72%", never as a probability claim like "72%
  chance of passing" — reviewed as part of Phase 7.5; no wording changes were needed since the
  Phase 7 backend/mobile copy already used the correct framing throughout.

## Demo/seed data

All seed content used in development is clearly flagged in the database. `companies`, `jobs`, and
`scholarships` already carry an `is_demo` boolean column (see `scripts/seed_demo_data.py`); the same
convention applies to questions/applications/news once those tables exist. Demo content must never be
presented to a production user as a real, current vacancy or opportunity — the mobile/admin UI should
visibly badge `is_demo` records once real-vs-demo content coexists in the same environment.

The 30 abstract-reasoning image questions seeded in Phase 7.5 (`scripts/generate_abstract_images.py`
+ `seed_abstract_image_questions.py`) are **original, procedurally-generated shapes** — not scans,
screenshots, or reproductions of any real commercial aptitude test — and are marked `is_demo=True`
like every other seeded question. The mobile UI continues to show the existing "CareerOS practice
assessment... not an official employer assessment" disclaimer wherever aptitude question content is
displayed (unchanged by this phase).
