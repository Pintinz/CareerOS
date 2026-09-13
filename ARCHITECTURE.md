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

## Recruitment email classification

Deterministic rule-based keyword/phrase classifier (`app/services/email_classifier.py`), not an LLM
call to an external API. Confidence-scored match against a specific `applications` row using company,
job title, reference number, and timing signals — the app **never** silently changes an application's
stage; it always asks for user confirmation (see `PRIVACY.md`).

## Environment-gated integrations

| Integration | Interface | Mock/dev provider | Real provider needs |
|---|---|---|---|
| Google Sign-In | `AuthProvider` | `MockAuthProvider` | `GOOGLE_CLIENT_ID` |
| Apple Sign-In | `AuthProvider` | `MockAuthProvider` | Apple Developer capability |
| Gmail tracking | `EmailProvider` | `MockEmailProvider` | Google OAuth client + `gmail.readonly` scope |
| Outlook tracking | `EmailProvider` | `MockEmailProvider` | Microsoft Graph app registration |
| AdMob | `AdProvider` | test ad unit IDs | production `ADMOB_APP_ID` |
| Push notifications | `PushProvider` | local-notifications only | FCM server key / APNs cert |

See `PROJECT_STATUS.md` → "Blocked by Credential / Tooling" for current status of each.
