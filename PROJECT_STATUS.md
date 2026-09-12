# CareerOS — Project Status

Last updated: 2026-09-12

This file is the single source of truth for build progress. Update it after every phase.

## Git

- Repo initialized 2026-09-12.
- `9357753` — Foundation + Phase 1 auth (tagged `phase-1-baseline`).
- `9593281` — Phase 2/3/4 backend+admin, mobile toolchain installed and verified from scratch.
- `1c0608f` — Mobile screens for Phase 2 (Opportunities)/3 (ATS)/4 (Company Intelligence).
- Everything under "Phase 5 — Applications" below is the next commit.

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

`flutter analyze`/`test`/`build apk --debug` have now been run clean **four times** across this
session as features were added (Phase 0/1 screens, then Phase 2/3/4, then Phase 5) — each rebuild
faster than the last since everything is cached:
- Toolchain-only build (first ever): 175.6MB APK, ~9 attempts to resolve (one-time cost — see git log
  on commit `9593281` for the full diagnosis: Maven Central rate-limiting, two outdated Gradle-
  incompatible plugins, one missing Android config).
- Phase 2/3/4 screens added: 201.3MB APK, built in **118 seconds**.
- Phase 5 (Applications) added: 201.3MB APK, built in **31 seconds**.

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundation | DONE | Monorepo scaffolded, all 3 apps boot and were verified live. |
| 1 — Auth + Profile | IN PROGRESS | Backend + mobile screens built and verified. Not built: Google/Apple Sign-In, forgot-password, email verification, settings screen. |
| 2 — Opportunities | IN PROGRESS | Backend + admin web + mobile screens all built and verified (real APK build). Missing: internships/graduate-programme sub-tabs (reuse the jobs model), career-preferences-driven "recommended" scoring. |
| 3 — ATS | IN PROGRESS | Backend + mobile screens (CV upload, analyze, results) built and verified. Missing: CV rename/set-primary controls in the mobile UI. |
| 4 — Company Intelligence | IN PROGRESS | Backend + mobile screens (feed, detail, follow, company profile) built and verified. Admin CMS UI for intelligence posts NOT built (API-only). |
| 5 — Applications | IN PROGRESS | Backend + mobile screens (list, detail w/ timeline, stage update, notes, manual + from-job creation) built and verified. Missing: document attachments (needs the general document vault), email-detected stage confirmation (Phase 8). |
| 6 — Aptitude Testing | NOT STARTED | |
| 7 — Interview Preparation | NOT STARTED | |
| 8 — Email Tracking | NOT STARTED | |
| 9 — Admin | IN PROGRESS | Jobs/Companies/Scholarships CMS built. Intelligence posts, question bank, source registry, discovery queue, user management NOT STARTED (or API-only). |
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

## Partially Complete

- **Mobile app**: Phase 0-5 core loops written and verified. Not yet built: internships/graduate-
  programme-specific UI, CV rename/set-primary, career-preferences-driven personalization anywhere,
  application document attachments.
- Admin web: no UI yet for intelligence posts (API-only).

## Not Started

- Mobile: Google/Apple Sign-In, forgot-password, email verification, settings, profile-setup wizard
  beyond name/location/experience, aptitude/interview prep screens (Prepare tab is still an honest
  empty state).
- Admin web: intelligence post CMS UI, question bank, source registry, discovery queue, user mgmt.
- Everything under Phases 6-11 (aptitude engine, interview prep, email classifier, AdMob integration
  code, production hardening).

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
API change, and a save/unsave toggle that silently no-op'd outside the main list's state).

## Tests

- Backend: `pytest -q` → **58 passed** across 8 test files (health, auth, admin/companies, jobs,
  scholarships, uploads, ATS, intelligence, applications).
- Admin: no automated tests — verified by hand via live browser interaction.
- Mobile: `flutter test` → 1 passing smoke test (app boots to splash). Widget/unit tests for the
  Phase 2-5 screens are still a Next Task — verification so far is `analyze` (type/lint correctness)
  + real APK builds (compiles and packages) + manual reasoning about data flow, not automated
  behavioral tests of the screens themselves.

## Known issues to revisit

- `npm audit` on `admin/` reports advisories against Next.js 14.2.35 (fixed only as of Next 16) —
  revisit in Phase 11 or before any non-localhost exposure.
- `ProfileUpdate` can't clear a field to null — `None`/omitted means "leave unchanged."
- Admin web stores its JWT in `localStorage` — fine for local dev, revisit before non-localhost use.
- `ScholarshipRepository.list_public`'s `degree_level` filter does a text-LIKE on the JSON column's
  string form rather than a real JSON containment query — fine at this scale.
- The `recommended` job/scholarship sort is a documented placeholder (featured-first, then newest).
- ATS job-title scoring is a keyword-overlap proxy, not structural CV parsing — documented as such.
- No admin CMS UI for intelligence posts yet.
- No mobile widget/unit tests for any Phase 2-5 screens yet — see Tests section above.
- `ApplicationUpdate` (`PUT /applications/{id}`) intentionally cannot change `current_stage` — only
  `/stage` can, so every stage change leaves a timeline entry. Make sure any future mobile "quick
  edit" form respects this and doesn't try to slip a stage change through the generic update.

## Next Tasks

1. Commit the Phase 5 (Applications) backend + mobile work — currently uncommitted.
2. Widget tests for the save/unsave flows and the application stage-update flow, given how many real
   bugs this session's manual review process has caught in exactly this kind of code.
3. Phase 6 (Aptitude Testing) or Phase 7 (Interview Preparation) — whichever the user prioritizes,
   or an admin CMS UI for intelligence posts to close out Phase 9's remaining gap.
