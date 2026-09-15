# CareerOS — Architecture

## Overview

Three deployable applications share one PostgreSQL database (accessed only by the backend):

```
┌─────────────┐        ┌──────────────┐        ┌────────────────┐
│  Flutter    │  HTTPS │   FastAPI    │  SQL   │   PostgreSQL    │
│  mobile app │ ─────► │   backend    │ ─────► │   database      │
└─────────────┘        └──────┬───────┘        └─────────────────┘
                               │ HTTPS (admin-only endpoints, RBAC)
                        ┌──────▼───────┐
                        │  Next.js     │
                        │  admin portal│
                        └──────────────┘
```

- The mobile app and the admin portal both talk to the **same backend**, never to the database directly.
- Admin-only routes live under `/api/v1/admin/*` and require an `admin_users` JWT with role claims
  (`SUPER_ADMIN`, `ADMIN`, `EDITOR`, `REVIEWER`). Consumer routes under `/api/v1/*` use a separate
  `users` JWT. The two token types are not interchangeable.
- All external integrations (Google/Apple Sign-In, Gmail/Outlook OAuth, AdMob, push notifications) are
  implemented behind an interface with a mock/dev provider, selected via environment configuration, so
  the product runs fully in dev without any of those credentials (spec Rule 3).

## Database engine notes (Phase 9.5)

This diagram's "PostgreSQL database" is the **target** production database; in practice this
project has only ever run against local SQLite (`app/db/session.py` falls back to
`sqlite+aiosqlite:///./careeros_dev.db` when `DATABASE_URL` isn't set to a Postgres URL — Docker
was never installed in this environment, see PROJECT_STATUS.md). This matters architecturally
because **SQLite does not enforce `FOREIGN KEY` constraints by default** — a Phase 9.5 audit found
this had never been turned on anywhere, meaning every `ondelete=CASCADE/RESTRICT/SET NULL` in
`app/models/*.py` was silently decorative until fixed. Both the production engine and the test
engine (`tests/conftest.py`) now register a `PRAGMA foreign_keys=ON` connect-event listener. This
has no effect on a real Postgres deployment (which enforces FKs natively and always has) — it only
matters because SQLite is what has actually been exercised. See DATABASE.md and SYSTEM_AUDIT.md §22
for the full finding.

## Backend layering (`backend/app/`)

```
api/          FastAPI routers — request/response only, no business logic
schemas/      Pydantic request/response models
services/     business logic (matching engine, ATS scoring, email classifier, etc.)
repositories/ SQLAlchemy queries, one repository per aggregate
models/       SQLAlchemy ORM models
security/     password hashing, JWT issuance/verification, RBAC dependencies
workers/      background jobs (APScheduler/Celery) — ingestion, digest emails, expiry sweeps
ingestion/    source adapters (RSS, Lever, Ashby) feeding the discovery queue
matching/     deterministic scoring: job match, ATS readiness, scholarship eligibility
```

Rule: routers depend on services, services depend on repositories, repositories depend on models.
Never skip a layer (a router must not construct raw SQL queries).

## Mobile layering (`mobile/lib/`)

Feature-first clean architecture. Each folder under `features/<name>/` follows:

```
data/         DTOs, remote/local data sources
domain/       entities, repository interfaces, use cases
presentation/ screens, widgets, Riverpod providers/controllers
```

Cross-cutting concerns live in `core/` (networking, storage, utils) and are the only things a feature
is allowed to import from outside its own folder (plus `theme/`, `routing/`, `widgets/`).

## Scoring engines (deterministic, not AI)

Three engines compute their scores from explicit, documented weights stored in backend config
(`app/matching/`), never from an LLM and never randomly:

1. **Job Match Score** — role/title similarity, skill overlap, industry, experience level, location,
   work-mode preference, education, keyword similarity (TF-IDF/cosine where useful).
2. **ATS Readiness Score** — **implemented** (`app/matching/ats_engine.py`), weights in
   `app/matching/ats_weights.py` (keyword coverage 25%, technical skills 20%, experience 20%,
   job title 10%, formatting 10%, education 5%, completeness 5%, placement 5% — see `API.md`).
   Keyword extraction is frequency-ranked unigrams/bigrams (`app/matching/text_utils.py`), with a
   small explicit synonym table (`app/matching/synonyms.py`, e.g. PLC ↔ "programmable logic
   controller") so a CV and JD using different wording for the same concept still match. Every
   response includes the full per-component breakdown, never a bare percentage.
3. **Scholarship Eligibility Match** — not yet implemented. Nationality, degree, field, academic
   level, experience, age, language, test requirements, country eligibility — expressed as
   ✓ / △ / ✕ per criterion, never as a blanket "you are eligible."

All three must describe themselves accurately as rules/similarity-based, per spec Rule 8 (no fake AI).

## Aptitude assessment engine (`app/aptitude/`, Phase 6)

Also deterministic/rules-based, not AI:

- **Generation** (`app/aptitude/generator.py`) — samples the requested count of active questions from
  the requested categories/difficulty. For `MIXED` difficulty, targets a 30/45/20/5 (easy/medium/hard/
  expert) split and backfills any shortfall from other difficulties rather than erroring when the bank
  is thin. Job/field-specific runs bias Technical questions toward relevant topics via a pure keyword
  lookup table (`app/aptitude/technical_topic_map.py` — e.g. "Process Technician" → Pumps, Valves,
  Compressors, P&IDs, DCS, SCADA, ...), falling back to the full category pool if too few topic-matched
  questions exist. "Practice Weak Areas" instead passes an explicit `topic_slugs` override, bypassing
  the job-title inference entirely — same underlying selection code, different topic source.
- **Snapshot-then-grade** — session creation copies every selected question's full content into
  `test_session_questions` (see `DATABASE.md`). This is the single mechanism that satisfies "editing a
  question later must never change a past session": nothing at grading/review time re-reads the live
  `questions` table.
- **Timer authority** — `expires_at` is a server timestamp, not a client-side countdown. Every session
  read/mutate call in `AptitudeService` first checks whether `expires_at` has passed and, if so, grades
  and closes the session inline (a "lazy auto-submit," not a background job — this stack has no
  Celery/APScheduler wired up yet) before doing anything else. A client can never keep answering, or
  keep a session alive, past its expiry just by not calling submit.
- **Grading** (`app/services/aptitude_service.py`) — per-question-type: choice questions (including
  `IMAGE_BASED`/`PASSAGE_BASED`, which are graded as single-choice — a documented simplification, since
  the spec's question-type enum conflates presentation with response mechanism) by exact selected-
  option-set match; `NUMERIC` by tolerance comparison. Overall score is marks-weighted (respects
  `marks`/`negative_marks`); `section_breakdown` is a simple per-category accuracy percentage — a
  deliberate, documented difference in aggregation style from the marks-weighted overall score, chosen
  to match the spec's plain-language "Numerical 87%" example.
- **Performance labels** are threshold-based ("Strong Performance" / "Good Performance" / "Needs
  Improvement"), never a random pass/fail, with thresholds centralized in `app/aptitude/scoring.py`.
  Weak-topic recommendations require a minimum of 3 attempted questions in a topic before that topic's
  accuracy is used, to avoid drawing conclusions from a tiny sample.

## Mobile aptitude offline behavior (`mobile/lib/features/aptitude/`)

Once a test session is loaded, it must survive a temporary connectivity loss or the app being
backgrounded/restarted (spec §20-21):

- `AptitudeOfflineCache` (SharedPreferences-backed — see note below) mirrors the full session detail
  (questions, options, current answers/flags, `expires_at`) to local storage on every load and every
  successful sync, and a pending-mutation queue for answers/flags made while offline.
- `ExamController` loads from the server first; if that fails and a cached session already exists, it
  keeps working from the cache rather than blocking the user with an error screen, flagging
  `hasUnsyncedChanges` so the UI can show an honest "not synced yet" indicator. Pending mutations are
  replayed opportunistically (on load, and before every new mutation) rather than via a connectivity-
  listener package.
- The countdown timer is computed from `expires_at` and a one-time device-clock-to-server-clock offset
  captured at load time, re-evaluated every second — never a bare `Timer` counting down from a fixed
  duration, so an app restart mid-test resumes with the correct remaining time. The backend's own lazy
  auto-submit check is still the actual authority; the client timer only decides when to *call* submit.
- This uses `SharedPreferences` (already the app's local key-value store — see `AppPreferences`)
  rather than the `drift` SQLite dependency declared in `pubspec.yaml`, which nothing in this codebase
  actually wires up yet (no generated database exists anywhere in `mobile/lib`). A single JSON blob per
  active session is a proportionate amount of local-storage machinery for this one feature; introducing
  a full Drift schema for it would be disproportionate scope. Worth revisiting if a future phase needs
  genuine relational local storage (e.g. an offline job feed) — at that point migrating this cache onto
  the same mechanism becomes worthwhile.

## Mobile interview offline behavior (`mobile/lib/features/interview/`)

Mirrors `AptitudeOfflineCache`'s approach almost exactly (spec §36): `InterviewOfflineCache`
(SharedPreferences-backed, same rationale for not using the unwired `drift` dependency — see
"Mobile aptitude offline behavior" above) caches the full session detail and a pending-mutation
queue for answers made while offline, replayed opportunistically on load and before each new
mutation. Since there's no server-enforced timer to keep synchronized, the offline story is
simpler than aptitude's: there's nothing analogous to a clock-offset calculation, only "keep
working from the cache, sync when possible." STAR stories, the preparation checklist, and
analytics are fetched fresh each time rather than offline-cached — a narrower scope than the
active session itself, and a documented gap (see PROJECT_STATUS.md).

## Interview preparation engine (`app/interview/`, Phase 7)

Also deterministic/rules-based, structurally similar to the aptitude engine but a separate,
uncoupled implementation (per explicit spec instruction — "reuse the aptitude taxonomy where
appropriate without coupling the two engines incorrectly"):

- **Generation** (`app/interview/generator.py`) — selects questions per category (evenly across
  selected categories, or per an explicit `category_counts` map for the Mock Interview builder's
  "Technical 4 / Behavioral 3 / Safety 2 / HR 1" style configuration). Job-specific Technical-topic
  bias uses its own keyword lookup table (`app/interview/job_role_topic_map.py`) — deliberately not
  the aptitude engine's `technical_topic_map.py`, since interview prep needs process/behavioral
  topics (shift handover, emergency response) with no aptitude-question equivalent. Company bias
  (preferring questions editorially tagged to a specific `company_id`) and topic bias are tried as
  independent, progressively looser fallback tiers (topic+company → topic-only → company-only →
  general) rather than ANDed into one filter — a job-specific session shouldn't fail to prefer
  "Pumps" questions just because none of them happen to be tagged to that job's company.
- **Junior gating** (spec §7) — a `MIXED`-difficulty session excludes `EXPERT` questions when the
  caller declares `ENTRY`/`JUNIOR` experience level; explicitly requesting `EXPERT` difficulty always
  overrides this.
- **Snapshot-then-grade-free** — same rationale as aptitude's `test_session_questions`:
  `interview_session_questions` freezes every question's guidance/evaluation points/STAR tags at
  session-creation time, so editing the master bank never changes a past session.
- **No server-enforced timer** — `time_per_question_seconds` is shown to the user during a Mock
  Interview but is purely self-paced/informational; unlike the aptitude engine's `expires_at`
  authority, nothing here auto-submits or rejects an answer when it elapses. This is a deliberate,
  documented difference: interview answers are open-ended text/audio a person is still composing,
  not a fixed multiple-choice grading window.
- **Answer Structure Check** (`app/interview/answer_check.py`, spec §22-23) — deterministic word
  count, metric-presence (regex digit check), and STAR-keyword-hint detection on a typed answer.
  Explicitly never labeled "AI analysis" anywhere in code, schemas, or UI copy.
- **STAR completeness check** (`app/interview/star_check.py`, spec §15) — each of
  Situation/Task/Action/Result is independently classified `missing`/`brief`/`complete`(/`strong`
  for Action with a detected first-person pronoun), plus named gaps (`missing_measurable_outcome`,
  `very_short_action`, `no_clear_personal_contribution`, ...). Computed fresh on every read from the
  stored text — never cached, so it can't go stale relative to an edit. No AI grading.
- **STAR-to-question matching** (spec §16) — a question's `star_tags` (lowercase snake_case values
  matching `StarCategory`, e.g. `"equipment_failure"`) are compared against the categories of the
  user's own STAR stories; any match surfaces that story's id in `suggested_star_story_ids`. Pure
  tag/category comparison, no AI.
- **Readiness** (`app/interview/readiness.py`, spec §11/§25) — six weighted components (Question
  Practice 25%, STAR Coverage 25%, Company Prep 15%, Job-Specific Prep 15%, Technical Prep 15%,
  Recent Consistency 5%), each a real activity count capped against a configurable target
  (`app/interview/scoring.py`). When Company/Job-Specific components don't apply (no
  `application_id` given), they're **excluded and the remaining weights renormalized** — never
  silently treated as zero, which would otherwise understate general (non-application-linked)
  readiness. Below `MIN_ACTIVITY_FOR_READINESS` combined signal, returns `insufficient_data: true`
  and `overall: null` rather than a fabricated number.
- **Company/role preparation** (spec §9) reuses existing CareerOS data — `companies`,
  `intelligence_posts` (company-scoped, via the same `IntelligenceRepository.list_public` the
  public `/intelligence` feed uses), and `jobs` (other open roles at that company) — plus the
  job-role topic map for "likely topics." It never claims to know a company's actual interview
  questions; every response carries a fixed disclaimer (spec §35, see also PRIVACY.md).

## Shared media pipeline (`app/services/storage_provider.py`, Phase 7.5)

One `StorageProvider` abstraction (`LocalStorageProvider` for dev, designed for an
`S3CompatibleStorageProvider`/`SupabaseStorageProvider` later — no cloud credentials required this
phase) backs **every** feature that needs an uploaded image: it already served the admin web upload
widget before Phase 7.5, and Phase 7.5 deliberately extended it in place rather than building a
second, parallel implementation for aptitude/interview question images (explicit spec instruction:
"do not create completely separate upload/storage implementations").

- `save_image_with_metadata` actually decodes every upload with Pillow (`Image.open(...).verify()`)
  before writing it to disk — rejects content that merely claims to be an image via
  extension/Content-Type but doesn't decode, extracts real width/height/mime-type/file-size, and
  enforces a max dimension (`MAX_DIMENSION_PX = 4096`) and the pre-existing max upload size.
- Every upload through `POST /admin/uploads/image` creates a `MediaAsset` row (`app/models/media.py`)
  — storage key, URL, mime type, dimensions, file size, optional alt text — a lightweight audit trail
  shared across features, not a per-feature table.
- Storage keys are randomized (`uuid4()` + extension), never derived from the client-supplied
  filename — defends against path traversal and filename collisions; this predates Phase 7.5 and was
  simply carried forward, now explicitly documented.
- `Question.question_image_alt_text` / `QuestionOption.option_image_alt_text` follow the exact same
  immutable-snapshot pattern Phase 6 established for every other question field: they're copied into
  `test_session_questions`/`options_snapshot` at session-creation time, so editing a master
  question's image or alt text later can never alter a past session — proven by a test that mutates
  the master question mid-session and asserts the session detail is unchanged.
- Alt text for Abstract-reasoning images is written to describe visual **structure** only ("A
  sequence of three rotating arrows, followed by a question mark panel"), never which option is
  correct — screen-reader accessible without leaking the answer.

## Original (non-copyrighted) abstract-reasoning image generation (`backend/scripts/`, Phase 7.5)

`generate_abstract_images.py` renders real PNG assets procedurally with Pillow's `ImageDraw`
primitives — rotation arrows, shape-count sequences, mirrored asymmetric shapes, odd-one-out shape
sets, checkerboard matrices — each mathematically parameterized (e.g. a rotation question's correct
answer is always exactly `start_angle + 3*step`), never copied from or resembling any real
commercial aptitude test. `seed_abstract_image_questions.py` seeds 30 of these as real, `is_demo`
`IMAGE_BASED` questions, idempotently (re-running it is a no-op once the images already exist).

## Offline-conflict versioning (`StarStory.version`, `InterviewPreparationProgress.version`, Phase 7.5)

Both models carry an integer `version`, default 1, incremented on every server-side write. Update
schemas (`StarStoryUpdate`, `ChecklistUpdate`, `QuestionToAskUpdate`, `TopicReviewUpdate`) accept an
optional `expected_version`; a mismatch raises 409 Conflict rather than silently applying the write.
This is deliberately a version counter, not a wall-clock timestamp comparison — two devices editing
offline can have clocks that drift or are simply wrong, but an integer that only the server
increments can't be spoofed into looking "newer" by a client with a fast clock. The **mobile** side
of conflict resolution (an offline mutation queue that carries `expected_version` and surfaces a
conflict to the user rather than silently overwriting) is not yet built — see PROJECT_STATUS.md.

## Interview audio recording (`mobile/lib/features/interview/`, Phase 7.5)

- `RecordingService` (`data/recording_service.dart`) wraps the `record` package's `AudioRecorder`
  behind a small interface returning a typed `RecordingException` (`RecordingErrorKind`: permission
  denied/permanently denied, mic unavailable, interrupted, storage failure, file missing, playback
  failure) for every failure mode — nothing it does can crash the interview session; a failure just
  means the typed-answer/notes fields remain the only way to answer that question. The underlying
  `AudioRecorder` is constructed **lazily** (on first actual use, not in the constructor) so a fully
  fake subclass used in tests never touches a real platform channel unless a test actually calls
  `start()`.
- Microphone permission (`permission_handler`) is requested **only** inside `startRecording()` —
  never during app bootstrap — per explicit spec instruction, satisfied by construction rather than
  by a runtime check (there is no code path that calls `Permission.microphone.request()` outside
  this one method).
- `RecordingController` (`presentation/recording_controller.dart`, one instance per
  `RecordingTarget` = session + session-question id via Riverpod's `.family`) owns the
  record/pause/stop/cancel/play/delete state machine and syncs a stopped recording's metadata to
  `POST /interview/recordings` (best-effort — a sync failure never blocks the local file or the
  in-session answer state). Playback uses `audioplayers`' `AudioPlayer`, constructed lazily for the
  same testability reason as the recorder — though unlike `AudioRecorder`, `AudioPlayer`'s own
  constructor opens a real platform/event channel unconditionally even from a subclass, so playback
  itself has no unit-test coverage, only `flutter analyze`/`build apk --debug` verification.
- The one-time consent dialog (`recording_widgets.dart`'s `ensureRecordingConsent`) is gated by a
  single `SharedPreferences` boolean, shown before the first recording attempt only, regardless of
  which question or session it happens in.
- Audio never uploads anywhere: `InterviewRecording.upload_status` stays `"local_only"` because no
  upload code path exists (by design, not by omission) — only the metadata row (duration, title,
  which question) is synced, never the audio bytes themselves.

## Smart Recruitment Email Tracking (`app/email_tracking/`, `app/services/email_tracking_*.py`, Phase 8)

**Security-sensitive by design — read this section before touching any of this code.** The single
governing rule: nothing outside `POST /email-tracking/events/{id}/confirm` may ever write to
`Application.current_stage`, and that endpoint only ever gets there by calling the *existing* Phase 5
`ApplicationService.update_stage` — there is no second, parallel transition implementation anywhere
in this phase. The full data flow, matching spec's own diagram exactly:

```
Recruitment email detected (webhook or reconciliation sync)
        ↓
Recruitment pre-filter (app/email_tracking/classifier.py — is this even recruitment-related?)
        ↓
Application matching (app/email_tracking/matcher.py — weighted signals, config in matching_config.py)
        ↓
Stage classification (app/email_tracking/classifier.py — phrase dictionaries, config-driven)
        ↓
Confidence calculation (app/email_tracking/confidence.py — combines classifier + matcher signals)
        ↓
RecruitmentEmailEvent persisted (status: SUGGESTED / AMBIGUOUS / UNMATCHED / DETECTED)
        ↓
User reviews it on the "Recruitment Update Detected" screen
        ↓
USER CONFIRMS (or picks the right application first, if AMBIGUOUS)
        ↓
EmailTrackingService.confirm_event() → ApplicationService.update_stage(..., source="EMAIL_CONFIRMED")
        ↓
ApplicationStageEvent appended (same table/mechanism as every manual stage change)
```

### Provider abstraction (`app/services/email_tracking_providers.py`)

One `EmailTrackingProvider` interface — `build_authorization_url`, `exchange_code`,
`refresh_access_token`, `establish_watch`/`renew_watch`, `list_changed_message_ids`,
`fetch_message`, `revoke` — with three implementations:

- `GmailTrackingProvider` / `OutlookTrackingProvider` — structurally real (genuine OAuth endpoints,
  genuine Gmail/Graph API calls via `httpx`), but **never exercised against a real Google or
  Microsoft account in this environment** — no production OAuth credentials are configured here.
  Gmail requests only `gmail.readonly`; Outlook requests only delegated `Mail.Read`/`User.Read`/
  `offline_access` for the signed-in user's own mailbox — no write/send/modify/delete scope is ever
  requested, and Outlook auth targets `common` (personal + work/school accounts), never a
  tenant-wide application permission.
- `MockEmailTrackingProvider` — a fully in-memory, deterministic double used by every automated test
  in this codebase and by the "mock connect flow" the mobile app's OAuth screens actually complete
  against in this environment. `EmailTrackingService.get_provider()` falls back to this
  automatically whenever a provider's real credentials aren't configured (see
  `Settings.gmail_tracking_available`/`outlook_tracking_available` in `app/core/config.py`) — the
  feature stays fully usable in dev with zero credentials, per explicit spec instruction.

### OAuth state (CSRF protection)

The provider's OAuth callback is hit directly by the user's browser — it carries no CareerOS bearer
token. A dedicated `oauth_states` table (random, single-use, 15-minute-lived, bound to
`(user_id, provider)`) is what lets the callback recover which CareerOS user initiated the flow
safely; an unknown, expired, or already-consumed state value is rejected with 400, never silently
accepted. This is the mobile-OAuth equivalent of a server-side session, deliberately not a JWT,
since it must be usable by an unauthenticated request.

### Token encryption (`app/services/token_encryption_service.py`)

`TokenEncryptionService` wraps `cryptography`'s `MultiFernet` (AES-128-CBC + HMAC-SHA256,
authenticated — not homemade crypto). Every access/refresh token is encrypted before it's written to
`email_connections`; `EmailConnectionOut` has no token field, encrypted or otherwise, so a normal API
response cannot leak one even by mistake. The key comes from `TOKEN_ENCRYPTION_KEYS` (a
comma-separated list, newest first) — `MultiFernet` encrypts with the first key and can decrypt with
any of them, which is what makes rotation possible without breaking already-stored ciphertexts.

### Deterministic classification (no generative AI anywhere)

`app/email_tracking/classifier.py` normalizes subject+body text and phrase-matches it against
`stage_phrases.STAGE_PHRASES`, a config-driven dictionary keyed directly by the **existing**
`ApplicationStage` enum values (spec §20 — no separate taxonomy to keep in sync; a detected stage
feeds straight into the Phase 5 stage endpoint with zero translation). A fixed priority order
resolves overlapping phrases (e.g. "final interview" language always wins over generic "interview"
language). Critically, `NEGATIVE_CONTEXT_PATTERNS` — general/aggregate phrasing like "only
shortlisted candidates will be contacted" — is checked independently and penalizes confidence
heavily (spec §23's mandatory rule: general recruitment information must never be read as a direct
statement about the recipient).

### Application matching (`app/email_tracking/matcher.py`, weights in `matching_config.py`)

A pure-function weighted scorer (`ApplicationSignal` dataclasses in, no ORM/database dependency) —
job/reference-id match (35), company/domain match (20), job-title word-overlap (20), an explicit
"Reference:"-labeled id (15), timing plausibility (5), location (5), normalized to 0–1. Returns
`matched` only when exactly one candidate clears `MATCH_MIN_SCORE` and beats every rival by more
than `MATCH_AMBIGUITY_MARGIN`; returns `ambiguous` with the full candidate list when several are too
close to call (spec §25's "three Shell applications" scenario); returns `unmatched` rather than ever
guessing. All weights and thresholds live in one module — spec §24's explicit "do not scatter
weights through code."

### Confidence model (`app/email_tracking/confidence.py`)

Combines the classifier's text-only signals (stage-language strength, recipient-directed phrasing,
known-ATS-domain sender) with the matcher's per-candidate signals (identifier/company/role/timing
match) into one 0–1 score, labeled HIGH/MEDIUM/LOW off centrally configured thresholds
(`matching_config.CONFIDENCE_HIGH`/`CONFIDENCE_MEDIUM`/`SUGGEST_MIN_CONFIDENCE`). A LOW-confidence
or sub-`SUGGEST_MIN_CONFIDENCE` event never becomes an intrusive suggestion — see
`EmailTrackingService.process_message`. Mobile copy is always phrased as a possibility ("CareerOS
detected a possible interview invitation"), never a certainty ("You passed!") — spec §27.

### Webhook processing (spec §13-14) and background-task abstraction

`POST /webhooks/gmail`/`/webhooks/microsoft`/`/webhooks/microsoft/lifecycle` (`app/api/v1/
webhooks.py`) each validate → deduplicate → acknowledge → enqueue, never running classification
before returning a response to the provider. `app/services/background_tasks.py`'s
`BackgroundTaskRunner` interface has exactly one implementation today, `InlineTaskRunner` (runs the
enqueued work immediately, in-process) — no Redis/Celery is wired up anywhere in this codebase yet
(same pre-existing gap as every other background-job mention in this file). Swapping to a real
queue later means writing one new `BackgroundTaskRunner` implementation; none of the webhook routes
need to change.

A Gmail Pub/Sub notification means "this mailbox changed," never "this is a recruitment email" —
the webhook handler fetches the connection matching the notified address, then defers to
`EmailTrackingService.sync_connection`, which calls `history.list` from the connection's own stored
`gmail_history_id` before anything is classified. A notification for an unknown or inactive mailbox
is a quiet no-op (spec §9/§43 — not an error, never a hint to the caller about which mailboxes exist
in the system). Microsoft's subscription-creation `validationToken` handshake is implemented exactly
per Graph's requirement; lifecycle events (`reauthorizationRequired`, `subscriptionRemoved`,
`missed`) mark the connection, attempt safe resubscription, or trigger a reconciliation sync
respectively (spec §12) — tracking never just silently stops.

### Idempotency

The database itself enforces "the same provider message never creates two events": `
recruitment_email_events` has a `UniqueConstraint(user_id, provider, provider_message_id)`, and
`RecruitmentEmailEventRepository.try_add` catches the resulting `IntegrityError` inside a SAVEPOINT
and returns `None` rather than raising — a redelivered webhook is a safe no-op, not a duplicate
suggestion or a crash. The confirm endpoint is separately idempotent: a second confirm attempt on an
already-`CONFIRMED` event returns 409, and `ApplicationService.update_stage(..., commit=False)`
combined with `EmailTrackingService.confirm_event`'s single final commit means the stage change and
the event's confirmed flag either both land or neither does — see `PROJECT_STATUS.md`'s Known Bugs
for the real atomicity bug this caught before it shipped.

### Watch/subscription renewal (spec §58-59)

`EmailTrackingService.renew_expiring_watches()` re-establishes any Gmail watch or Outlook
subscription within 24 hours of expiry, and marks a connection `REAUTHORIZATION_REQUIRED` outright
if its stored token can't even be decrypted or if renewal fails with a non-retryable auth error (see
"Background job scheduler" under Phase 9 below — as of Phase 9 this now runs for real, every 24
hours, wrapped in the shared retry/backoff policy).

### Forward-to-CareerOS (spec §36)

`EmailForwardingAlias` gives each user a random opaque token (`apply+<token>@<configured domain>`),
never a sequential/guessable id — implemented as a real table + repository. No inbound-mail provider
(an inbound-parse webhook from a transactional-email vendor, for instance) is configured in this
environment, so `Settings.forward_email_available` stays `false` and the feature is inert end to
end — exactly the "implement the architecture, don't block the phase" outcome the spec itself asks
for when a provider isn't available (spec §36's explicit fallback instruction).

## Admin CMS, content operations & background scheduling (`app/scheduler.py`, `app/services/
retry_policy.py`, `app/models/admin_ops.py`, `app/services/admin_ops_service.py`, Phase 9)

Full detail lives in **ADMIN.md**. Architecturally significant points:

### Background job scheduler (`app/scheduler.py`)

A single `AsyncIOScheduler` (APScheduler) wired into FastAPI's `lifespan`, started/stopped alongside
the app process — deliberately **not** placed under `app/workers/` (that directory remains an empty
placeholder from the original scaffold; the scheduler and its jobs live directly in
`app/scheduler.py` and `app/services/content_lifecycle_service.py` instead, since no second
process/queue exists to justify a separate `workers/` package yet). Three jobs are registered:
email watch/subscription renewal (24h), scheduled content publishing (15min), content expiration
(1h), plus — since the live discovery engine — a discovery dispatcher (5min: due sources + queued
runs + stale runs) and active-listing re-verification (12h); see **DISCOVERY_ENGINE.md**. Each job run's outcome (last run,
success, duration, error) is tracked in an in-memory, process-local history and surfaced via
`GET /admin/dashboard/operations` — this history is intentionally not persisted, since it describes
"since this backend process last started," not a durable audit trail (that's what `AuditLog` is for).

### Retry/backoff policy (`app/services/retry_policy.py`)

A reusable `RetryPolicy` classifies any exception into `TRANSIENT`/`AUTHORIZATION`/`CONFIGURATION`/
`INVALID_REQUEST`/`PROVIDER_OUTAGE`/`UNKNOWN` (HTTP 401/403 → `AUTHORIZATION`, 429/5xx →
`TRANSIENT`, other 4xx → `INVALID_REQUEST`) and retries only transient/outage categories with
exponential backoff + jitter up to a bounded attempt count, raising `PermanentFailure(category, ...)`
otherwise. `EmailTrackingService._renew_one()` is the first (and currently only) consumer — an
`AUTHORIZATION` failure marks the connection `REAUTHORIZATION_REQUIRED`, anything else marks it
`ERROR`, and a connection is never retried forever on a permanent failure. Any future scheduled job
that calls an external provider should reuse this policy rather than writing its own try/except.

### Content workflow, sources, and discovery

Job/Scholarship/IntelligencePost each gained `scheduled_publish_at`/`reviewed_by_admin_id`/
`published_by_admin_id`, populated idempotently by each service's `create`/`update` via a shared
`_apply_workflow_transitions` pattern (duplicated per-service rather than extracted into one shared
mixin — a minor inconsistency, not a bug). `ContentSource`/`DiscoveredItem` (in
`app/models/admin_ops.py`) are now populated by the live discovery engine (**DISCOVERY_ENGINE.md**):
`app/ingestion/` holds the safe HTTP client, deterministic adapters (Lever, Greenhouse, Ashby,
SmartRecruiters, experimental Workday, RSS, schema.org pages), validated extraction schemas and the
`ResearchProvider` abstraction (structured / web / Anthropic / mock); `app/services/discovery/` holds
the pipeline (organization matching, deduplication, change detection, removal detection), the
publishing/change-application helpers, re-verification, the queue worker and the admin review
service. Discovered content reaches users only through an admin publish action, or through
auto-publishing when every gate passes (off by default). Public feeds show only listings still active
at their source; detail pages expose an `availability` state (`app/services/availability.py`).

### Audit logging and settings

`AuditLog` (`app/models/admin_ops.py`) is a plain append-only table — no ORM-level protection
against update/delete exists, but no code path ever calls one; `audit_service.record()` is the only
writer. `SystemSetting` is a generic key/JSON-value store; `system_settings_service.KNOWN_SETTINGS`
is the registry of what's editable, but wiring a stored setting into the code that should actually
use it is a separate, per-setting task — only the email-classifier confidence thresholds are wired
as of Phase 9 (see PROJECT_STATUS.md's Phase 9 section for the full list of what's stored-but-not-
yet-consumed).

## Direct company career feeds (`app/ingestion/adapters/`, `app/services/discovery/`)

Official employer career sources flow through the same discovery pipeline as every other source:
adapter → validation → dedup → change detection → queue → admin/publishing policy → app. Adapters are
per **provider** (Greenhouse, Lever, Ashby, Workday, Oracle Recruiting Cloud, schema.org official pages via
JSON-LD/microdata/listing pages/sitemaps) and configured per employer in the source registry, so adding a
company is data (`app/seeds/career_sources.json` or the admin Sources page), not code. Sources can be
scoped to countries/regions (Workday and Oracle scope server-side through the site's own facets). A
listing missing from a complete source listing is `POSSIBLY_REMOVED` until repeated confirmation, then
`SOURCE_REMOVED` pending admin confirmation. Details: **CAREER_SOURCE_INTEGRATION.md**.

## Environment-gated integrations

| Integration | Interface | Mock/dev provider | Real provider needs |
|---|---|---|---|
| Google Sign-In | `AuthProvider` | `MockAuthProvider` | `GOOGLE_CLIENT_ID` |
| Apple Sign-In | `AuthProvider` | `MockAuthProvider` | Apple Developer capability |
| Gmail tracking | `EmailProvider` | `MockEmailProvider` | Google OAuth client + `gmail.readonly` scope |
| Outlook tracking | `EmailProvider` | `MockEmailProvider` | Microsoft Graph app registration |
| AdMob | `AdService` (`lib/core/monetization/ad_service.dart`) | Google's official test ad units (`AdUnitConfig`) | real AdMob account + real App IDs + real ad unit IDs via `--dart-define` |
| Push notifications | `PushProvider` | local-notifications only | FCM server key / APNs cert |

See `PROJECT_STATUS.md` → "Blocked by Credential / Tooling" for current status of each.

## Monetization architecture (`lib/core/monetization/`, `app/services/monetization_service.py`, Phase 10)

Full detail in **MONETIZATION.md**. Architecturally significant points:

- **One `AdService` abstraction** — no screen constructs `BannerAd`/`InterstitialAd`/`RewardedAd`
  directly. `AdUnitConfig` resolves the correct ad unit id per platform/format, with an explicit
  fail-safe: a genuine production build with no real ad unit configured for a format disables it
  outright rather than silently falling back to Google's test units (never the reverse — test
  traffic must never look like real inventory, nor should a real build silently serve nothing
  without an obvious cause). `AdFrequencyController` (pure, unit-tested) is the single source of
  truth for interstitial pacing — no screen makes its own frequency decision.
- **Consent is Google's own UMP SDK**, wrapped by `ConsentManager` — this codebase has no
  homemade consent dialog anywhere, matching the same "use the real mechanism, don't invent one"
  discipline applied elsewhere (e.g. Phase 8's OAuth flows use real provider SDKs, not custom
  token handling).
  App Open ads are architected (`AdFormat.appOpen`, test/production ad unit ids exist) but
  `MonetizationConfig.appOpenAdsEnabled` is hardcoded `false` client-side regardless of the
  backend value — a deliberate defense-in-depth guarantee, not just a default, since no screen
  should ever be able to accidentally enable it via a server misconfiguration.
- **Entitlement is backend-computed, not client-trusted**: `GET /monetization/entitlement`
  reports FREE/PRO status and today's usage from a live UTC-calendar-day query against the
  existing `AtsAnalysis`/`TestSession` tables — no separate counter table, no reset job. The
  reward ledger (`RewardUnlock`, `reward_unlocks` table) uses a database-level
  `UniqueConstraint` on a client-generated `reference_id` as its idempotency mechanism, the same
  pattern already established for Phase 8's email-event dedup and Phase 9's discovery dedup —
  this codebase consistently prefers a database constraint over an application-level check for
  "this exact thing must never happen twice" guarantees.
- **Reuses Phase 9's `system_settings` architecture** for all non-secret ad/frequency
  configuration (`monetization_config`, `free_tier_limits`) — no new admin backend or frontend
  code was needed; both keys appear automatically in the existing generic settings editor.
