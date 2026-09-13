# CareerOS — Project Status

Last updated: 2026-09-13

This file is the single source of truth for build progress. Update it after every phase.

## Git

- Repo initialized 2026-09-12.
- `9357753` — Foundation + Phase 1 auth (tagged `phase-1-baseline`).
- `9593281` — Phase 2/3/4 backend+admin, mobile toolchain installed and verified from scratch.
- `1c0608f` — Mobile screens for Phase 2 (Opportunities)/3 (ATS)/4 (Company Intelligence).
- `1a58ef3` — Phase 5 (Applications) backend + mobile.
- `6775869` — Phase 6 (Aptitude Testing) backend + mobile (tagged `phase-6-aptitude`).
- `d9fe06f` — Phase 7 (Interview Preparation & STAR) backend + mobile (tagged `phase-7-interview`).
- `5d221b3` — Phase 7.5 (Media, Assessment & Interview Hardening) backend + mobile (tagged `phase-7.5-media-hardening`).

## Environment notes (read before assuming anything is verified)

- **Flutter SDK, JDK 17 (zip), Android SDK: installed** this session at `C:\flutter`, `C:\jdk17`,
  `C:\Android` — none of it existed on this machine before. Set up per-session via `dev-env.sh`
  (gitignored, machine-specific). See `DEPLOYMENT.md` → "Mobile toolchain setup" for the permanent
  Windows environment-variable equivalent.
- **Docker: still NOT installed.** `docker-compose.yml` is written but never run; backend dev/test uses
  local SQLite (`DATABASE_URL` swaps cleanly to Postgres once available).
- **Python 3.13 and Node.js: available and used**, backend/admin verified live throughout.
- iOS: cannot be built or verified at all on this machine (Windows, no macOS/Xcode).

## Mobile toolchain — verified green, and staying green

`flutter analyze`/`test`/`build apk --debug` have now been run clean **six times** across this
session as features were added (Phase 0/1 screens, then Phase 2/3/4, then Phase 5, then Phase 6,
then Phase 7) — each rebuild faster than the last since everything is cached:
- Toolchain-only build (first ever): 175.6MB APK, ~9 attempts to resolve (one-time cost — see git log
  on commit `9593281` for the full diagnosis: Maven Central rate-limiting, two outdated Gradle-
  incompatible plugins, one missing Android config).
- Phase 2/3/4 screens added: 201.3MB APK, built in **118 seconds**.
- Phase 5 (Applications) added: 201.3MB APK, built in **31 seconds**.
- Phase 6 (Aptitude Testing) added: 192.1MB APK, built in **125 seconds**.
- Phase 7 (Interview Preparation) added: 192.2MB APK, built in **86 seconds**.
- Phase 7.5 (Media & Interview Hardening) added: real audio recording (`record`/`audioplayers`/
  `permission_handler`) plus a required `record` 5.2.0→7.1.1 bump (see Known Bugs) — 192.4MB APK,
  built in **~5 minutes** cold (Maven Central intermittently 403'd mid-resolution on the new
  `permission_handler_android`/AGP-8.0.0-buildscript transitive tree; retried clean).
- Phase 7.5 follow-up (Mock Interview Mix UI) added: 192.4MB APK, built in **39 seconds**.

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundation | DONE | Monorepo scaffolded, all 3 apps boot and were verified live. |
| 1 — Auth + Profile | IN PROGRESS | Backend + mobile screens built and verified. Not built: Google/Apple Sign-In, forgot-password, email verification, settings screen. |
| 2 — Opportunities | IN PROGRESS | Backend + admin web + mobile screens all built and verified (real APK build). Missing: internships/graduate-programme sub-tabs (reuse the jobs model), career-preferences-driven "recommended" scoring. |
| 3 — ATS | IN PROGRESS | Backend + mobile screens (CV upload, analyze, results) built and verified. Missing: CV rename/set-primary controls in the mobile UI. |
| 4 — Company Intelligence | IN PROGRESS | Backend + mobile screens (feed, detail, follow, company profile) built and verified. Admin CMS UI for intelligence posts NOT built (API-only). |
| 5 — Applications | IN PROGRESS | Backend + mobile screens (list, detail w/ timeline, stage update, notes, manual + from-job creation) built and verified. Missing: document attachments (needs the general document vault), email-detected stage confirmation (Phase 8). |
| 6 — Aptitude Testing | IN PROGRESS | Backend (question bank, snapshot-based sessions, deterministic generation/grading, analytics) + mobile (Prep Hub, configuration, exam screen, navigator, results, review, analytics, application/home/profile integration) built and verified. Missing: real image assets for Abstract-reasoning questions (text/emoji placeholders), per-section timing (only overall timing built), Company-Specific mode UI (architected, not built per spec). |
| 7 — Interview Preparation | IN PROGRESS | Backend (10-category question bank, snapshot-based sessions, deterministic generation/self-paced mock timer/company+job bias, STAR stories + completeness check + question matching, readiness/analytics, company-research prep) + mobile (Interview Home, configuration, session screen, results, STAR builder, analytics/readiness, company prep + checklist, application/home/profile integration) built and verified. Real audio recording landed in Phase 7.5 (see below); still missing: per-category Mock Interview count builder **UI** (backend now fully supports it, see Phase 7.5), offline caching of STAR stories/checklist/analytics (only the active session itself is offline-cached). |
| 7.5 — Media, Assessment & Interview Hardening | IN PROGRESS | Backend: shared image-upload pipeline hardened with real Pillow decode validation + `MediaAsset` audit rows, `question_image_alt_text`/`option_image_alt_text` (immutably snapshotted like every other question field), 30 real procedurally-generated (non-AI, non-copyrighted) abstract-reasoning images seeded, `StarStory.version`/`InterviewPreparationProgress.version` for offline conflict detection (409 on stale `expected_version`), `InterviewRecording` metadata model + CRUD, centralized role-specific Mock Interview mix config (`app/interview/role_mix.py`) + preview endpoint. Mobile: real microphone recording/playback wired into the interview session screen (record/stop/play/delete, consent dialog, every failure mode mapped to a message, never a crash), `version`-aware STAR/PreparationProgress models ready for offline sync, and (follow-up) a real Automatic Mix / Custom Mix builder in the Mock Interview configuration screen. Missing (see Known limitations): abstract-image rendering/caching/zoom in the aptitude UI, offline STAR/checklist CRUD with conflict resolution, cache-management screen, Recordings Manager screen, retention settings, resume-active-activity, unified preparation history. |
| 8 — Email Tracking | NOT STARTED | |
| 9 — Admin | IN PROGRESS | Jobs/Companies/Scholarships/Aptitude/Interview question-bank CMS **APIs** built (admin web UI for aptitude/interview questions not built — Phase 9 UI work). Intelligence posts, source registry, discovery queue, user management NOT STARTED (or API-only). |
| 10 — Monetization | NOT STARTED | `google_mobile_ads` dependency present (bumped to 9.1.0 for Gradle compat) but no ad integration code exists yet. |
| 11 — Production Hardening | NOT STARTED | |

## Completed

### Phases 0-4 (see git log for `9357753`, `9593281`, `1c0608f` for full detail)
Foundation, auth/profile, opportunities (jobs/scholarships/companies, backend+admin+mobile), ATS
(backend+mobile), company intelligence (backend+mobile). 58 backend tests, all passing.

### Phase 5 — Applications (backend AND mobile, verified)
**Backend** (`app/models/application.py`, `app/services/application_service.py`,
`app/api/v1/applications.py`):
- `applications`/`application_stage_events`/`application_notes` tables. An application can reference
  a real `job_id` (auto-fills company/role/location/job_url) or be entered manually for a role not in
  our `jobs` table (spec §36) — strictly user-owned, every route 404s on another user's application
  rather than leaking existence via 403.
- `current_stage` can **only** change via `POST /applications/{id}/stage`, which always appends an
  `application_stage_events` row — there is no way to silently change a stage, mirroring the "never
  silently change a stage" principle spec §42 states for email-detected updates, applied here even
  for manual updates.
- `GET /me/applications-summary` backs the Home dashboard's "Active Applications" card with a real
  count (excludes HIRED/REJECTED/WITHDRAWN/EXPIRED) — not a placeholder number.
- 9 tests: manual creation validation, creation-from-job field prefill, per-user isolation (404 not
  403 on another user's application), stage update appends timeline + updates current_stage, notes
  CRUD, stage filtering, active-count excludes terminal stages, deletion.

**Mobile** (`lib/features/applications/`):
- `ApplicationListScreen` — stage filter chips (all 19 stages + "All"), pull-to-refresh, FAB to add
  a manual entry.
- `ApplicationDetailScreen` — Details/Timeline/Notes tabs, a visual timeline (newest-first, checked
  circles for past stages, an open circle for the current one — spec §36's example), "Update Stage"
  bottom sheet (`RadioGroup` over all 19 stages + optional note), inline note composer, delete with
  confirmation, "View Job" opens the real external URL when available.
- Stage-aware hints (spec §38): an info banner appears for APTITUDE_TEST/INTERVIEW/FINAL_INTERVIEW/
  MEDICAL stages. Since Phases 6/7 (aptitude/interview prep) don't exist yet, this is **informational
  text only** — no "Prepare" button pointing at a screen that isn't built, which would violate spec
  Rule 2 (no placeholders for things that could instead just not be shown yet).
- `CreateApplicationScreen` — manual entry form (company, role, location, job URL).
- Entry points: a job's detail screen ("Track This Application" → creates from that job), Home
  dashboard (real "Active Applications" count card, tappable), Profile → "My Applications".

### Phase 6 — Aptitude Testing (backend AND mobile, verified)

**Backend** (`app/models/question.py`, `app/models/test_session.py`, `app/aptitude/`,
`app/services/aptitude_service.py`, `app/api/v1/aptitude.py`, `app/api/v1/admin/aptitude.py`):
- Real question-bank data model (`question_categories`/`question_topics`/`questions`/
  `question_options`) and a real session data model with a **snapshot table**
  (`test_session_questions`) that freezes every question's content at session-creation time — editing
  or deleting a master question later cannot alter a past session's grading or review (see
  `ARCHITECTURE.md` → Aptitude assessment engine, `DATABASE.md`).
- Deterministic (non-AI) generation engine: mixed-difficulty distribution with graceful backfill when
  the bank is thin, and job/field-specific Technical-topic bias via a pure keyword lookup table — no
  AI call anywhere in the selection path.
- Timer authority lives in `expires_at` on the server; every session read/mutate lazily checks expiry
  and auto-submits inline before doing anything else, so a client can never out-wait or bypass a timed
  session's deadline.
- Backend-authoritative grading (marks-weighted overall score with negative marking; per-question-type
  logic; accuracy-based section breakdown), qualitative performance labels (never a random pass/fail),
  and real analytics/recommendations computed from the user's actual submitted-session history (with a
  minimum-attempt threshold before a topic counts as "weak").
- "Practice Weak Areas" is a real, working feature end to end: `TestSessionCreate.topic_slugs`
  overrides the generator's topic preference directly, and `GET /aptitude/recommendations` returns each
  weak topic's slug specifically so the mobile client can feed it straight back in.
- 404-not-403 ownership isolation (matching Applications) on every session/review/result route.
- Admin CRUD API for the question bank exists (categories/topics/questions/options, role-gated like
  jobs/scholarships) even though the admin web UI for it is deferred to Phase 9.
- 141 real demo questions seeded (`scripts/seed_aptitude_questions.py`): Numerical 26, Verbal 26,
  Abstract 21, Logical 20, Technical 32, Situational Judgement 16 — every question has a real correct
  answer, explanation, topic, and difficulty. Abstract-reasoning questions use text/emoji shape
  sequences rather than real images (documented limitation — no image-asset pipeline exists yet for the
  question bank; `question_image_url` stays null on every seeded question rather than being faked).
- 17 new backend tests (session creation/generation/no-duplicates, per-user isolation, answering and
  changing an answer pre-submit, flagging, submit + negative-marking + unanswered-question grading,
  cannot modify or re-grade after submit, review hidden pre-submit, timer expiry auto-submits and then
  independently rejects further answers, remaining-seconds reporting, analytics + weak-topic-threshold
  gating, job-specific topic selection via a real linked job, `topic_slugs` override for Practice Weak
  Areas, application linkage that never mutates the real application's stage, admin question-bank CRUD
  + non-admin-access rejection).

**Mobile** (`lib/features/aptitude/`):
- Preparation Hub (replaces the old Prepare-tab placeholder): "What are you preparing for?" with a real
  Aptitude Test card and an honest, disabled "Interview Preparation — Coming in Phase 7" card (never a
  dead button that does nothing when tapped), real stats (Tests Completed/Average Score/Questions
  Practiced/Best Score) from `GET /aptitude/analytics`, and a recent-tests list.
- Test configuration screen: mode selection (Practice/Timed/Mock/Job-Specific/Field-Specific —
  Company-Specific intentionally not exposed in the UI, per spec), section multi-select, difficulty
  (Easy/Medium/Hard/Mixed), question count (10/20/30/40/60), and timing (Untimed/Overall Timer — per-
  section timing is a documented gap, see Known limitations). Job-Specific/Field-Specific modes let the
  user pick from their own tracked applications to source the job context, reusing the existing
  applications data rather than building a separate job picker.
- Active exam screen: header (section name, "Question N of M", timer badge), progress bar, question
  rendering (single/multiple-choice, numeric entry, image and passage support), Previous/Next/Flag/
  Navigator/Submit controls, no ad placement. The countdown is computed from `expires_at` and a captured
  device-to-server clock offset, re-evaluated every second — not a naive in-memory countdown — so an
  app restart or backgrounding mid-test resumes with the correct remaining time.
- Question Navigator (bottom sheet): Current/Answered/Unanswered/Flagged states with a legend and a
  tap-to-jump grid.
- Submit confirmation dialog with answered/unanswered/flagged counts and remaining time; auto-submits
  without a confirmation dialog when the timer actually reaches zero.
- Offline behavior: session/questions/answers/flags/timestamps are cached locally (SharedPreferences —
  see `ARCHITECTURE.md` for why not Drift), answers persist immediately and sync incrementally, and a
  pending-mutation queue replays once connectivity returns, with an honest "not synced yet" indicator
  in the exam header rather than silently dropping answers.
- Results screen (score, time used, correct/incorrect/unanswered, section breakdown, strongest/weakest
  areas, Review/Retake/Done) and a post-submission-only question review screen (your answer vs. correct
  answer, explanation) — the review screen is unreachable before submission because the backend itself
  refuses the request (409), not just because the mobile UI hides a button.
- Analytics screen: real stats, per-section breakdown, weak-topic recommendations, and a working
  "Practice Weak Areas" button that starts a new session using the real `topic_slugs` from those
  recommendations.
- Real integration points: application detail screen shows a genuine "Prepare for Aptitude Test" button
  (not just informational text) when `current_stage == APTITUDE_TEST`, preselecting that application's
  job context — practicing never mutates the application's real stage. Home dashboard gets a real
  "Preparation Progress" card and an "Upcoming Recruitment Stage" card when an application is at that
  stage. Profile gets a real "Aptitude Performance" entry.
- 21 new Flutter widget tests (Prep Hub content/navigation/real-stats, mode/section/difficulty/count/
  timing configuration and test start, question rendering/answer selection/next-previous/flagging/
  navigator/timer display, submit confirmation dialog, results screen, post-submit review screen,
  analytics screen + Practice Weak Areas navigation, application "Prepare for Aptitude Test" button
  presence and absence) — 22 total together with the pre-existing splash-boot smoke test, all passing.

### Phase 7 — Interview Preparation & STAR (backend AND mobile, verified)

**Backend** (`app/models/interview.py`, `app/interview/`, `app/services/interview_service.py`,
`app/api/v1/interview.py`, `app/api/v1/admin/interview.py`):
- Real question-bank data model (`interview_question_categories`/`interview_topics`/
  `interview_questions`) with the ten fixed categories from spec §6, plus a real session data
  model with the same **immutable snapshot pattern** as aptitude
  (`interview_session_questions`) — editing a master interview question later can never alter a
  past session's guidance, evaluation points, or STAR tags.
- Deterministic (non-AI) generation: even distribution across selected categories, or an explicit
  `category_counts` map for a Mock Interview's fixed "Technical 4 / Behavioral 3 / Safety 2 / HR 1"
  style builder. Company bias (questions editorially tagged to a specific employer) and job-role
  Technical-topic bias (a keyword map separate from aptitude's, since interview topics like "shift
  handover" have no aptitude-question equivalent) are tried as independent fallback tiers rather
  than ANDed together — a real bug caught and fixed during this phase (see Known Bugs).
- Junior-candidate gating (spec §7): a `MIXED` session excludes `EXPERT` questions for declared
  `ENTRY`/`JUNIOR` experience levels unless `EXPERT` difficulty is explicitly requested.
- No server-enforced timer for Mock Interview — `time_per_question_seconds` is self-paced/
  informational only, a deliberate and documented difference from the aptitude engine's
  server-authoritative `expires_at` (open-ended interview answers aren't a fixed-choice grading
  window). See ARCHITECTURE.md.
- Deterministic "Answer Structure Check" (word count, metric-presence, STAR-keyword hints) and a
  deterministic STAR completeness check (per-section `missing`/`brief`/`complete`/`strong` status
  plus named gaps like `missing_measurable_outcome`) — neither is ever called "AI analysis" or "AI
  grading" anywhere in code, schemas, or copy, per explicit spec instruction.
- STAR-to-question matching: a question's `star_tags` are compared against the categories of the
  user's own STAR stories to populate `suggested_star_story_ids` — pure tag comparison, no AI.
- Readiness calculation with spec §11's exact six weighted components, each derived from real
  stored activity and capped against a configurable target; components that don't apply (no
  `application_id` given) are excluded and the remaining weights renormalized rather than treated
  as zero; below a minimum-activity threshold, returns `insufficient_data: true` instead of a
  fabricated number.
- Company/role preparation reuses real CareerOS data (companies, company-scoped intelligence
  posts, other open jobs at that company) with a fixed, honest disclaimer that this is CareerOS
  practice, never a claim to know a company's actual interview questions (spec §9/§35).
- A persisted company-research checklist (7 fixed items) and a curated "questions to ask the
  interviewer" catalog (18 questions across 9 categories) that users can save/mark-planned/extend
  with their own questions.
- 404-not-403 ownership isolation on every session/STAR/progress route, matching aptitude/
  applications. Admin CRUD API for the question bank exists, role-gated like aptitude/jobs, even
  though the admin web UI for it is deferred to Phase 9.
- 213 real demo questions seeded (`scripts/seed_interview_questions.py`): HR/General 27,
  Behavioral 30, Technical 41 (Mechanical/Process, Data/Analytics, Software, General workplace),
  Safety 20, Leadership 20, Management 20, Situational 20, Career Motivation 15, Company-Specific
  10, Job-Specific 10 — every question has real, hand-written `answer_guidance`/
  `evaluation_points`, never AI-generated or presented as employer-official.
- 16 new backend tests (question generation and best-available-set behavior, per-user isolation,
  answering + completion stat computation, cannot modify answers after completion, company-specific
  question preference, job-specific topic preference via a real linked job, application-linked
  session resolves job/company context and never mutates the real application's stage, readiness
  insufficient-data-then-real-score transition, analytics reflecting real activity, STAR CRUD +
  isolation, STAR completeness gap reporting, STAR-to-question matching, checklist/topic-review
  persistence, admin question-bank CRUD + non-admin-access rejection).

**Mobile** (`lib/features/interview/`):
- Preparation Hub's Interview card is now real (replacing the Phase 6 "Coming in Phase 7" disabled
  state) with its own "Start Preparing" entry point and real stats (Interview Sessions/Questions
  Practiced/STAR Stories Ready/Interview Readiness) from live analytics/readiness endpoints.
- Interview Home hub: Quick Start (Mock Interview/Question Practice/STAR Story Builder/Readiness &
  Analytics) plus category tiles (Company-Specific/Job-Specific/Technical/Behavioral/HR-General/
  Safety/Leadership/Management), each launching the configuration screen preselected.
- Configuration screen: mode (Question Practice/Mock Interview), category multi-select, difficulty,
  question count, and an optional self-paced per-question timer for Mock Interview (explicitly
  labeled as reference-only, nothing auto-submits when it elapses).
- Session screen (shared by both modes): question text, category/difficulty badges, Show/Hide
  Guidance (what the interviewer is assessing, what a strong answer includes, common mistakes,
  technical concepts to mention), a typed-answer field with a live Answer Structure Check, a notes
  field, Mark as Practiced, Save (bookmark), a 1-5 self-rating row (Poor/Weak/Fair/Strong/
  Excellent), and three yes/no self-checks (Used STAR? / Gave a measurable result? / Answered the
  exact question?) — all explicitly user-declared, never system-inferred. Previous/Next/Skip/End
  Interview controls; a Mock Interview session shows the countdown badge.
- Results screen: questions completed/skipped, average self-rating, average answer length, STAR
  usage rate, per-category breakdown, areas practiced vs. still uncovered.
- STAR Story Builder: list screen with a completeness indicator per story; an editor with a live
  completeness card (Situation/Task/Action/Result status plus named gaps) that recomputes on save.
- Analytics/Readiness screen: the same "not enough activity" honesty pattern as aptitude when data
  is insufficient; otherwise a real overall percentage plus the six-component breakdown and
  activity stats.
- Company Preparation screen (application-linked): company overview, recent developments, role
  relevance, likely topics, other open roles, the persisted research checklist, and the curated
  questions-to-ask catalog with Save/Planned toggles and a custom-question composer.
- Real integration points: application detail screen shows a genuine "Interview Preparation" card
  (readiness/questions-practiced/STAR-ready stats, Company Research + Continue Preparation buttons)
  for Interview/Final Interview/Recruiter Screen/Assessment Centre stages — practicing never
  mutates the application's real stage. Home dashboard gets a real "Upcoming Interview Preparation"
  card with that application's actual readiness percentage. Profile gets a real "Interview
  Preparation" entry.
- Offline behavior: the active session (questions/answers/notes/self-ratings/flags) is cached
  locally and answers sync incrementally with a pending-mutation queue, mirroring the aptitude
  engine's approach — see Known limitations for what is *not* offline-cached (STAR stories,
  checklist, analytics).
- 16 new Flutter widget tests (Interview Home quick actions/category-tile navigation, mode/category
  configuration and session start, question rendering/guidance-reveal/answer+self-rating sync/
  next-previous/mock-timer-display, STAR story creation with concrete completeness gaps + list
  completeness indicator, company prep overview/disclaimer/checklist persistence, readiness
  insufficient-data-then-real-score + activity stats, application "Interview Preparation" card
  presence across all four interview-related stages, an already-cached session continuing to work
  when the server is unreachable) — 39 Flutter tests total together with Phases 6 and the original
  smoke test, all passing.

### Phase 7.5 — Media, Assessment & Interview Hardening (focused subset, verified)

This phase was explicitly scoped down from a 42-section spec to a focused, fully real subset —
see Known limitations for what was deliberately deferred rather than half-built.

**Backend** (`app/models/media.py`, `app/services/storage_provider.py`,
`app/api/v1/admin/uploads.py`, `app/interview/role_mix.py`, `app/services/interview_service.py`):
- The **existing** shared image-upload endpoint (`POST /admin/uploads/image`) — already used across
  the admin UI — was extended in place rather than duplicated: it now actually decodes every upload
  with Pillow (`.verify()`), rejects content that merely claims to be an image via
  extension/Content-Type but doesn't decode, extracts real width/height/mime/file-size, and writes a
  `MediaAsset` audit row. Storage keys stay randomized UUIDs (never derived from the client
  filename), unchanged from before.
- `Question.question_image_alt_text` / `QuestionOption.option_image_alt_text`: neutral structural
  descriptions ("A sequence of three rotating arrows, followed by a question mark panel") that never
  reveal an Abstract-reasoning answer. Both are snapshotted into `test_session_questions`/
  `options_snapshot` exactly like every other question field — a session's images/alt-text can never
  change after the fact even if the master question is edited later, verified by a test that mutates
  the master question mid-session and asserts the session detail is unchanged.
- `StarStory.version` / `InterviewPreparationProgress.version`: integers bumped on every write.
  `StarStoryUpdate`/`ChecklistUpdate`/`QuestionToAskUpdate`/`TopicReviewUpdate` all accept an
  optional `expected_version` — a mismatch returns 409 Conflict rather than silently overwriting a
  newer remote edit. This is the backend half of offline conflict handling; the mobile UI/queue that
  uses it (spec §21) is not yet built — see Known limitations.
- `InterviewRecording` model (`id`/`user_id`/`session_id`/`session_question_id`/`local_path`/
  `duration_seconds`/`title`/`upload_status`) — metadata only, `upload_status` stays `"local_only"`
  since no upload path exists (by design: audio never leaves the device automatically). Full CRUD at
  `POST/GET /interview/recordings`, `PUT/DELETE /interview/recordings/{id}`, owner-isolated
  (404-not-403, matching every other resource in this codebase).
- `app/interview/role_mix.py`: centralized, keyword-matched default category-mix-by-role config
  (e.g. Process/Operations → Technical 40%/Behavioral 25%/Safety 20%/HR 15%), mirroring the existing
  `job_role_topic_map.py` pattern rather than inventing a new one. `category_counts_for_mix` uses
  largest-remainder rounding so percentages always sum to exactly the requested question count — no
  category silently drops to zero. `GET /interview/sessions/mock-mix-preview` lets a client preview
  the distribution before creating a session; `InterviewSessionCreate.auto_mix=true` applies it.
- 30 real, original, procedurally-generated abstract-reasoning images
  (`scripts/generate_abstract_images.py`, Pillow `ImageDraw` primitives — rotation arrows, shape-count
  sequences, mirrored shapes, odd-one-out sets, checkerboard matrices; each mathematically
  parameterized, not copied from any real test) seeded as real `IMAGE_BASED` questions
  (`scripts/seed_abstract_image_questions.py`, idempotent, `is_demo=True`) — closes the Phase 6
  documented gap ("Abstract-reasoning questions use text/emoji placeholders").
- 9 new backend tests: image-upload metadata/validation (valid + disguised-as-image rejection),
  question/option image immutable snapshotting, STAR/checklist stale-`expected_version` 409s,
  recording CRUD + cross-user isolation, role-mix keyword matching + percentage-sum invariants, the
  mock-mix-preview endpoint against a real job.
- Caught and fixed one real pre-existing bug: `tests/test_uploads.py`'s "smallest possible valid PNG"
  fixture actually had a corrupted IDAT chunk checksum — invisible before this phase because the old
  validation never decoded image content, only checked headers/extension/Content-Type. The new
  Pillow-decode validation correctly rejected it; the fixture was regenerated with a genuinely valid
  Pillow-encoded PNG.

**Mobile** (`lib/features/interview/data/recording_service.dart`,
`lib/features/interview/presentation/recording_controller.dart`, `recording_widgets.dart`):
- Real microphone recording via the `record` package (`AudioRecorder`, AAC-LC), wired into the
  interview session screen as an explicit alternative to (and combinable with) the existing typed-
  answer/notes fields — never a requirement. Microphone permission (`permission_handler`) is
  requested **only** when the user taps Start Recording, never at app startup (Android
  `RECORD_AUDIO` + iOS `NSMicrophoneUsageDescription` both added accordingly).
- The one-time local-storage privacy notice ("Interview recordings are stored locally on this
  device unless you explicitly choose to upload or share them." / Continue / Not Now) shows once
  before the first recording attempt (persisted via `SharedPreferences`) and never again.
- Every recording/playback failure mode (permission denied, permanently denied, mic unavailable,
  interrupted, storage failure, file missing, playback failure) is caught into a typed
  `RecordingErrorKind` and surfaced as a message — never an uncaught exception; the typed-answer and
  notes fields on the same screen remain fully usable regardless of what recording did.
  `▶ 01:42`-style playback (via `audioplayers`) with Play/Pause/Delete controls.
- A completed recording both updates the in-session answer state (`audioPath`/
  `audioDurationSeconds`, synced through the existing offline-queue-aware `answer()` path — extended
  this phase to carry those two fields end-to-end alongside the pre-existing text/notes/self-rating
  fields) and syncs its own metadata row via `POST /interview/recordings` (best-effort; a sync
  failure never blocks the local recording or in-session answer).
- `StarStory`/`PreparationProgress` mobile models now carry `version` (defaulting to 1 for any
  cached data saved before this phase) and the repository's `updateStarStory`/`updateChecklistItem`/
  `updateQuestionToAsk`/`updateTopicReview`/`createSession` calls accept `expectedVersion`/
  `autoMix` — the data-layer prerequisite for the offline STAR/checklist sync UI that is not yet
  built (see Known limitations).
- 6 new Flutter tests covering the recording state machine (start→recording, permission-denied→error
  without crashing, stop→recorded with path+duration, a stop failure surfacing as an error rather
  than a crash, delete→idle, cancel→idle) via a fully fake `RecordingService` subclass — no real
  platform channel touched. Real audio playback (`audioplayers`) could not be similarly unit-tested:
  `AudioPlayer`'s own constructor opens a real platform/event channel unconditionally, even from a
  subclass, so there is no way to fake it without an actual platform — see Known limitations.

### Phase 7.5 follow-up — Mock Interview Mix UI (backend AND mobile, verified)

Closes the one Phase 7.5 gap explicitly called out as "backend-only, no mobile surface yet": the
Mock Interview configuration screen (`interview_configuration_screen.dart`) now has a real
Automatic Mix / Custom Mix builder, replacing the plain category multi-select whenever Mock
Interview mode is selected (Question Practice mode is unaffected — the mix concept doesn't apply to
Automatic Mix vs. Custom Mix there).

- **Automatic Mix** (default when Mock Interview is selected): calls the existing
  `GET /interview/sessions/mock-mix-preview` endpoint (`mockMixPreviewProvider`, keyed by question
  count + application/job id so it refetches when the question count changes) and renders the
  real role-specific split as badges (e.g. "Technical 4 / Behavioral 3 / Safety 2 / HR 1") plus a
  total, labeled "Role-specific split" or "General default split" depending on `source`. Starting
  the session passes `auto_mix: true` — the server derives `category_counts` itself, mirroring
  exactly what the preview showed.
- **Custom Mix**: a per-category stepper (−/count/+) for every interview category, with a running
  "Total: X / Y" indicator that turns red until the counts sum to exactly the selected question
  count — the Start button is disabled (with an explicit message) until they match, so a session
  can never be created with a silently-dropped or mismatched category split. Starting the session
  passes the non-zero counts as `category_counts` directly.
- 2 new Flutter widget tests: Automatic Mix shows the real preview and defaults to selected;
  Custom Mix disables Start until counts sum correctly, then enables it once they do — 47 Flutter
  tests total (up from 45).

## Partially Complete

- **Mobile app**: Phase 0-7.5 core loops written and verified. Not yet built: internships/graduate-
  programme-specific UI, CV rename/set-primary, career-preferences-driven personalization anywhere,
  application document attachments, per-section aptitude timing, abstract-reasoning image rendering
  in the active-test/review UI (the images/alt-text now exist end-to-end on the backend — see Phase
  7.5 — but the Flutter aptitude screens still render `question_image_url` with a plain
  `Image.network`, not yet swapped to a caching+zoom widget), offline caching/sync of STAR
  stories/checklist/interview analytics, cache-management screen, Recordings Manager screen,
  recording retention settings, resume-active-activity on the Preparation Hub, unified preparation
  history.
- Admin web: no UI yet for intelligence posts, the aptitude question bank, or the interview
  question bank (all three API-only).

## Not Started

- Mobile: Google/Apple Sign-In, forgot-password, email verification, settings, profile-setup wizard
  beyond name/location/experience.
- Admin web: intelligence post CMS UI, aptitude question-bank CMS UI, interview question-bank CMS UI,
  source registry, discovery queue, user mgmt.
- Everything under Phases 8-11 (email classifier, AdMob integration code, production hardening).

## Blocked by Credential / Tooling

- Docker not installed → Postgres/compose stack unverified.
- Google/Apple Sign-In, Gmail/Outlook OAuth, AdMob production IDs, FCM/APNs keys — none supplied;
  provider abstraction + mocks land when those specific phases are reached (spec Rule 3).
- Forgot-password needs a transactional email sender — not chosen/configured.
- iOS build cannot be attempted or verified on this machine at all (Windows, no macOS/Xcode).

## Known Bugs

None currently open. Full history of bugs found-and-fixed this session lives in the commit messages
for `9593281` and `1c0608f` (a nullable comparison bug, an admin form page-size mismatch, job expiry
not enforced everywhere, two Gradle-plugin incompatibilities, an `AppColors` typo, a `file_picker` v12
API change, and a save/unsave toggle that silently no-op'd outside the main list's state). Phase 6
caught and fixed one real bug before it shipped: an aptitude session created from `application_id`
alone was silently discarding the linked job's industry/title context (an early-return bug in
`AptitudeService._resolve_job_context`), which would have made Job-Specific practice from an
application never actually bias toward the right Technical topics — fixed and covered by
`test_job_specific_session_prefers_mapped_technical_topics` and the mobile
`application_prepare_button_test.dart`. Phase 7 caught and fixed one real bug before it shipped: the
interview generator's `_select_with_preference` combined topic bias and company bias into a single
ANDed database filter, so a job-specific session would fail to prefer topic-matched questions (e.g.
"Pumps") whenever none of them happened to also be tagged to that job's specific company — fixed by
trying topic+company, topic-only, company-only, and general as independent fallback tiers, covered
by `test_job_specific_generation_prefers_mapped_topics`. Phase 7.5 caught and fixed one real
pre-existing bug before it shipped: `tests/test_uploads.py`'s "smallest possible valid PNG" fixture
had a corrupted IDAT chunk checksum, invisible until this phase's Pillow-decode validation actually
opened the bytes — fixed by regenerating a genuinely valid Pillow-encoded fixture (see the Phase 7.5
section above). Phase 7.5 also hit one real dependency-resolution bug (not a code bug, but real
enough to block the build): `record: ^5.2.0` resolves an old `record_linux` (0.7.2) that doesn't
implement the newer `record_platform_interface` (1.6.0) another transitive dependency pulls in —
Flutter's own `AudioRecorder`/`record_linux` version matrix was inconsistent, unrelated to any
platform this app actually ships (Android/iOS) but still fatal to compilation since Flutter compiles
all federated platform implementations. Fixed by bumping to `record: ^7.1.1` (no `RecordingService`
API changes were needed — `flutter analyze`/`test` stayed clean before and after).

## Tests

- Backend: `pytest -q` → **100 passed** across 11 test files (health, auth, admin/companies, jobs,
  scholarships, uploads, ATS, intelligence, applications, aptitude, interview, **media & hardening —
  9 tests, new this phase**, in `test_media_and_hardening.py`).
- Admin: no automated tests — verified by hand via live browser interaction.
- Mobile: `flutter test` → **47 passed** (1 pre-existing splash-boot smoke test + 21 Phase 6 widget
  tests + 16 Phase 7 widget tests + 6 Phase 7.5 tests covering the recording state machine via a
  fully fake `RecordingService` — start/permission-denied/stop/stop-failure/delete/cancel; see the
  Phase 7.5 section above for why real `audioplayers` playback isn't similarly unit-tested — +
  **2 new Mock Interview Mix UI tests** (Automatic Mix shows the real preview, Custom Mix gates
  Start on counts summing correctly). Widget/unit tests for the Phase 2-5 screens are still a Next
  Task — this phase only added coverage
  for what it built.
- **Not performed**: interactive manual acceptance testing on a real device/emulator, for the same
  reason as Phase 6 (no Android emulator or physical device available in this environment). The four
  acceptance flows Phase 7 asks for are each covered by an equivalent automated test instead:
  Flow 1 (Behavioral practice → self-rating → completion → analytics update) by
  `test_answering_and_completion_computes_stats` + `test_analytics_reflects_completed_session_activity`
  (backend) and `interview_session_screen_test.dart` (mobile); Flow 2 (application-driven,
  job-specific, company+role preselected) by
  `test_application_linked_session_resolves_job_and_does_not_mutate_stage` +
  `test_job_specific_generation_prefers_mapped_topics` (backend) and
  `application_interview_prep_test.dart` (mobile); Flow 3 (STAR story creation → suggested for a
  matching question) by `test_question_to_star_matching_suggests_relevant_stories` (backend) and
  `star_story_editor_screen_test.dart` (mobile); Flow 4 (Mock Interview → answer/skip → completion →
  readiness/activity update) by the same completion + readiness backend tests and
  `interview_session_screen_test.dart`'s mock-mode test. This is real, passing, automated coverage of
  the same behavior — not the same as a person tapping through the built APK on a device, which has
  not happened for any phase in this session.

## Known issues to revisit

- `npm audit` on `admin/` reports advisories against Next.js 14.2.35 (fixed only as of Next 16) —
  revisit in Phase 11 or before any non-localhost exposure.
- `ProfileUpdate` can't clear a field to null — `None`/omitted means "leave unchanged."
- Admin web stores its JWT in `localStorage` — fine for local dev, revisit before non-localhost use.
- `ScholarshipRepository.list_public`'s `degree_level` filter does a text-LIKE on the JSON column's
  string form rather than a real JSON containment query — fine at this scale.
- The `recommended` job/scholarship sort is a documented placeholder (featured-first, then newest).
- ATS job-title scoring is a keyword-overlap proxy, not structural CV parsing — documented as such.
- No admin CMS UI for intelligence posts or the aptitude question bank yet (both API-only).
- No mobile widget/unit tests for any Phase 2-5 screens yet — see Tests section above.
- `ApplicationUpdate` (`PUT /applications/{id}`) intentionally cannot change `current_stage` — only
  `/stage` can, so every stage change leaves a timeline entry. Make sure any future mobile "quick
  edit" form respects this and doesn't try to slip a stage change through the generic update.
- 30 real abstract-reasoning image questions now exist in the seed data (Phase 7.5,
  `is_demo=True`, `question_image_url`/`question_image_alt_text` populated end-to-end through
  session snapshotting) alongside the 21 original text/emoji Abstract questions from Phase 6 — but
  the Flutter aptitude active-test/review screens still render `question_image_url` with a plain
  `Image.network` (no caching, no offline resilience, no zoom/fullscreen). Revisit before claiming
  the abstract-reasoning image experience is complete on mobile.
- Aptitude timing only supports "Untimed" and "Overall Timer" — `TestSession.time_limit_seconds` is a
  single overall value; there's no per-section time allocation in the schema. Per-section timing is not
  implemented, even though the spec lists it as an option. Documented rather than faked in the mobile
  configuration screen (only the two working options are shown).
- `TestMode.COMPANY_SPECIFIC` exists in the backend enum (spec asks for it to be architected, not
  built) but has no generation logic behind it and is not selectable in the mobile UI — selecting it
  via a raw API call would just behave like a normal session with no company-specific bias.
- No interactive manual QA pass on a real device/emulator for the Phase 6, 7, or 7.5 acceptance
  flows — see Tests section above for what automated coverage substitutes for it. Recording/
  playback in particular has never been exercised against a real microphone/speaker; only the
  fully-mocked state-machine tests and `flutter analyze`/`build apk --debug` back it.
- **Interview audio recording is now implemented** (Phase 7.5) — record/stop/play/delete, consent
  dialog, permission-timing, and every documented failure mode are real and covered by tests. Not
  yet built on top of it: a Recordings Manager screen (Profile → Interview Preparation → "Practice
  Recordings"), recording retention settings (keep-forever / 30-day / after-session-completion), and
  a "Storage & Offline Data" cache-management screen (spec §22-24) — recordings accumulate locally
  with no UI to review, rename, or bulk-delete them outside the one-recording-per-question controls
  on the session screen itself.
- ~~The Mock Interview per-category count builder UI was missing~~ — **built** (see the dedicated
  "Mock Interview Mix UI" entry below). Resolved.
- Interview offline caching covers only the active session (questions/answers/notes/self-ratings/
  recordings-in-progress) — STAR stories, the preparation checklist, and analytics/readiness are
  always fetched fresh and will show a loading/error state rather than cached data when offline.
  The backend now has everything needed for conflict-safe offline editing of STAR stories and the
  checklist (`version`/`expected_version`, 409-on-stale-write, Phase 7.5) and the mobile models
  (`StarStory.version`, `PreparationProgress.version`) already parse it — but the mobile offline
  cache, mutation queue, and conflict-resolution UI for STAR/checklist editing were not built this
  pass. Only the in-progress session itself is offline-cached.
- The Preparation Hub does not yet detect and surface an in-progress aptitude test or interview
  session ahead of new-session actions ("Continue Assessment"/"Continue Interview Practice" — spec
  §28), and there is no unified Aptitude+Interview preparation history view (spec §29) — both
  documented as not built rather than attempted partially.
- Interview readiness/analytics use targets (e.g. 30 questions practiced, 5 ready STAR stories) that
  are configured constants (`app/interview/scoring.py`), not derived from any research — same
  category of documented simplification as the aptitude engine's targets. Phase 7.5 did not move
  these into a separate `readiness_config` module as one spec section suggested (a naming/location
  change only, not a behavior change) — deferred as low-value relative to the phase's real gaps.

## Metrics: what's system-calculated vs. user self-rated vs. editorially tagged

Spec §46 requires this distinction never be blurred. As of Phase 7.5 (unchanged from Phase 7 —
Phase 7.5 added no new AI-adjacent scoring, only real recording/media/versioning infrastructure):

**System-calculated** (derived by backend code from stored activity, never user-editable):
Aptitude score/percentage/section breakdown/performance label; aptitude analytics (tests
completed, average/best score, category/topic accuracy) and weak-topic recommendations; interview
`Answer Structure Check` (word count, metric-presence, STAR-keyword hints); STAR completeness
(`sections`, `gaps`, `is_complete`); interview readiness (`overall` and all six components);
interview analytics (sessions completed, questions practiced, average self-rating *as an average
of user-submitted ratings*, STAR stories ready, company-prep-completed count, technical topics
covered, per-category completion); STAR-to-question `suggested_star_story_ids` matching.

**User self-rated** (the backend stores exactly what the user selects and never infers or
overrides it): interview answer `self_rating` (1-5), `used_star`, `gave_measurable_result`,
`answered_exact_question`; STAR story field content itself (situation/task/action/result/lessons/
metrics — the user writes these, the system only checks their *structure*, never their factual
truth or quality of writing).

**Editorially tagged** (admin-entered metadata, not evidence of anything factual): a question's
`company_id` (means "recommended practice for this company/role," never "this employer actually
asks this"); a question's `field`/`industry`/`job_role`/`experience_level`/`difficulty`; a
question's `star_tags` (which STAR categories it's a good match for — an editorial judgment, not a
computed similarity score); `answer_guidance`/`evaluation_points` (hand-written by whoever created
the question, deterministic content, never AI-generated or claimed to be employer-official).

## Next Tasks

1. Commit the Mock Interview Mix UI follow-up work — currently uncommitted.
2. Remaining mobile UI for backend capabilities that still don't have a mobile surface:
   abstract-reasoning image rendering with caching + zoom in the aptitude screens, a Recordings
   Manager + retention settings screen, a cache-management ("Storage & Offline Data") screen.
3. Offline STAR story + checklist editing with conflict resolution, now that the backend
   (`version`/`expected_version`, 409-on-stale-write) and mobile models are ready for it — the
   mutation queue and conflict UI are the remaining piece.
4. Widget tests for the save/unsave flows and the application stage-update flow (Phase 5 gap), given
   how many real bugs this session's manual review process has caught in exactly this kind of code.
5. Phase 8 (Email Tracking), or an admin CMS UI for intelligence posts / the aptitude+interview
   question banks to close out Phase 9's remaining gaps — whichever the user prioritizes. Per the
   user's explicit instruction, Phase 8 was NOT started automatically after Phase 7.5.
6. A real interactive QA pass on an emulator/device once one is available in this environment, to
   validate the Phase 6, 7, and 7.5 acceptance flows beyond what automated tests can confirm —
   recording/playback against a real microphone/speaker especially.
