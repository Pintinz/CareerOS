# CareerOS — Project Status

Last updated: 2026-09-12

This file is the single source of truth for build progress. Update it after every phase.

## Git

- Repo initialized 2026-09-12.
- `9357753` — Foundation + Phase 1 auth (tagged `phase-1-baseline`).
- `9593281` — Phase 2/3/4 backend+admin, mobile toolchain installed and verified from scratch.
- `1c0608f` — Mobile screens for Phase 2 (Opportunities)/3 (ATS)/4 (Company Intelligence).
- `1a58ef3` — Phase 5 (Applications) backend + mobile.
- `6775869` — Phase 6 (Aptitude Testing) backend + mobile (tagged `phase-6-aptitude`).

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

`flutter analyze`/`test`/`build apk --debug` have now been run clean **five times** across this
session as features were added (Phase 0/1 screens, then Phase 2/3/4, then Phase 5, then Phase 6) —
each rebuild faster than the last since everything is cached:
- Toolchain-only build (first ever): 175.6MB APK, ~9 attempts to resolve (one-time cost — see git log
  on commit `9593281` for the full diagnosis: Maven Central rate-limiting, two outdated Gradle-
  incompatible plugins, one missing Android config).
- Phase 2/3/4 screens added: 201.3MB APK, built in **118 seconds**.
- Phase 5 (Applications) added: 201.3MB APK, built in **31 seconds**.
- Phase 6 (Aptitude Testing) added: 192.1MB APK, built in **125 seconds**.

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
| 7 — Interview Preparation | NOT STARTED | |
| 8 — Email Tracking | NOT STARTED | |
| 9 — Admin | IN PROGRESS | Jobs/Companies/Scholarships/Aptitude question-bank CMS **APIs** built (admin web UI for aptitude questions not built — Phase 9 UI work). Intelligence posts, source registry, discovery queue, user management NOT STARTED (or API-only). |
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

## Partially Complete

- **Mobile app**: Phase 0-6 core loops written and verified. Not yet built: internships/graduate-
  programme-specific UI, CV rename/set-primary, career-preferences-driven personalization anywhere,
  application document attachments, per-section aptitude timing, real image assets for Abstract-
  reasoning questions.
- Admin web: no UI yet for intelligence posts or the aptitude question bank (both API-only).

## Not Started

- Mobile: Google/Apple Sign-In, forgot-password, email verification, settings, profile-setup wizard
  beyond name/location/experience, interview prep screens (the Prepare tab's Interview card is an
  honest disabled "Coming in Phase 7" state, not a placeholder screen).
- Admin web: intelligence post CMS UI, aptitude question-bank CMS UI, source registry, discovery queue,
  user mgmt.
- Everything under Phases 7-11 (interview prep, email classifier, AdMob integration code, production
  hardening).

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
`application_prepare_button_test.dart`.

## Tests

- Backend: `pytest -q` → **75 passed** across 9 test files (health, auth, admin/companies, jobs,
  scholarships, uploads, ATS, intelligence, applications, **aptitude — 17 tests, new this phase**).
- Admin: no automated tests — verified by hand via live browser interaction.
- Mobile: `flutter test` → **22 passed** (1 pre-existing splash-boot smoke test + 21 new Phase 6 widget
  tests across Prep Hub, test configuration, the active exam screen, submit confirmation, results,
  review, analytics, and the application "Prepare for Aptitude Test" button). Widget/unit tests for the
  Phase 2-5 screens are still a Next Task — this phase only added coverage for the screens it built.
- **Not performed**: interactive manual acceptance testing on a real device/emulator (no Android
  emulator or physical device is available in this environment — only `flutter analyze`/`test`/`build
  apk --debug`, which compiles, packages, and exercises the screens' logic via widget tests, but never
  actually launches the APK). The three acceptance flows the Phase 6 spec asks for (a full timed test
  happy path, a short-timed-test timeout/auto-submit path, an application-driven job-specific prep
  path) are each covered by an equivalent automated test instead: `test_expired_session_auto_submits_on_access_and_rejects_further_answers`
  (backend) + `active_test_screen_test.dart`'s timer-badge test (mobile) for the timeout path;
  `test_job_specific_session_prefers_mapped_technical_topics` (backend) +
  `application_prepare_button_test.dart` (mobile) for the application-driven path; the full
  session-creation-through-submission-through-review backend test chain plus the mobile exam-screen
  tests for the general happy path. This is real, passing, automated coverage of the same behavior —
  but it is not the same as a person tapping through the built APK on a device, which has not happened.

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
- Abstract-reasoning aptitude questions use text/emoji shape sequences, not real images — no image-
  asset pipeline exists yet for the question bank (`question_image_url` stays null on every seeded
  question). Revisit once admin image upload is wired to the question CMS.
- Aptitude timing only supports "Untimed" and "Overall Timer" — `TestSession.time_limit_seconds` is a
  single overall value; there's no per-section time allocation in the schema. Per-section timing is not
  implemented, even though the spec lists it as an option. Documented rather than faked in the mobile
  configuration screen (only the two working options are shown).
- `TestMode.COMPANY_SPECIFIC` exists in the backend enum (spec asks for it to be architected, not
  built) but has no generation logic behind it and is not selectable in the mobile UI — selecting it
  via a raw API call would just behave like a normal session with no company-specific bias.
- No interactive manual QA pass on a real device/emulator for the Phase 6 acceptance flows — see Tests
  section above for what automated coverage substitutes for it.

## Next Tasks

1. Commit the Phase 6 (Aptitude Testing) backend + mobile work — currently uncommitted.
2. Widget tests for the save/unsave flows and the application stage-update flow (Phase 5 gap), given
   how many real bugs this session's manual review process has caught in exactly this kind of code.
3. Phase 7 (Interview Preparation), or an admin CMS UI for intelligence posts / the aptitude question
   bank to close out Phase 9's remaining gaps — whichever the user prioritizes.
4. A real interactive QA pass on an emulator/device once one is available in this environment, to
   validate the Phase 6 acceptance flows beyond what automated tests can confirm.
