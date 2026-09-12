# CareerOS — Project Status

Last updated: 2026-09-12

This file is the single source of truth for build progress. Update it after every phase.

## Git

- Repo initialized 2026-09-12.
- Baseline commit: `9357753e2af2ee9e011abb37259e0112a2da5b84` — "feat: establish CareerOS foundation and
  Phase 1 authentication", tagged `phase-1-baseline`.
- Second commit: `9593281` — "feat: Phase 2 (Opportunities), Phase 3 (ATS), Phase 4 (Company
  Intelligence), and verified mobile toolchain" (backend/admin only — mobile screens below came after).
- Everything under "Mobile — Phase 2/3/4 screens" below is the next commit.

## Environment notes (read before assuming anything is verified)

- **Flutter SDK, JDK 17 (zip), Android SDK: installed** this session at `C:\flutter`, `C:\jdk17`,
  `C:\Android` — none of it existed on this machine before. Set up per-session via `dev-env.sh`
  (gitignored, machine-specific). See `DEPLOYMENT.md` → "Mobile toolchain setup" for the permanent
  Windows environment-variable equivalent.
- **Docker: still NOT installed.** `docker-compose.yml` is written but never run; backend dev/test uses
  local SQLite (`DATABASE_URL` swaps cleanly to Postgres once available).
- **Python 3.13 and Node.js: available and used**, backend/admin verified live throughout.

## Mobile toolchain verification — ALL GREEN, and stayed green through a second full feature pass

- `flutter doctor -v` / `pub get` / `analyze` / `test`: all clean.
- `flutter build apk --debug`: **GREEN**, twice now:
  - First green build (toolchain-only, Phase 0/1 screens): 175,603,508 bytes, SHA1
    `43c7e62094354b3e4c4de3c865d76b2739c20780`. Took 9 attempts to get the *toolchain* working — see
    "Mobile toolchain, first-time setup" below for the full diagnosis (network rate-limiting, two
    outdated Gradle-incompatible plugins, one missing Android config).
  - Second green build (after adding all Phase 2/3/4 mobile screens — see below): 201,271,208 bytes,
    SHA1 `17bc5604e23b63085634dd9e3df1f2264f9ad43a`, built in **118 seconds** — confirming the earlier
    9-attempt saga was genuinely one-time setup cost, not a recurring problem. Every dependency was
    already cached and every Gradle config issue was already fixed.
- `android/`/`ios/` platform folders generated via `flutter create . --org com.careeros
  --project-name careeros --platforms=android,ios` without touching existing `lib/`/`pubspec.yaml`.
- iOS: cannot be built or verified at all on this machine (Windows, no macOS/Xcode).

### Mobile toolchain, first-time setup (for the record)
1. **Network flakiness** (attempts 1-3): Maven Central / Gradle Plugin Portal intermittently 403'd
   concurrent artifact requests. Confirmed via direct `curl` (works standalone; 2/8 concurrent requests
   to the same URL got real 403s). Added `org.gradle.internal.repository.max.tentatives=10` /
   `...initial.backoff=500` to `android/gradle.properties`.
2. **Outdated plugin versions** (attempt 4): `google_mobile_ads` (was `^5.1.0`) and
   `flutter_secure_storage` (was `^9.2.2`) shipped Gradle scripts incompatible with Gradle 9.3.1.
   Bumped to `^9.1.0` / `^11.1.1`, cascading into `file_picker` → `^12.3.0` (transitive `win32`
   conflict, which also changed its API — see Known Bugs).
3. **Missing standard config** (attempt 8): `flutter_local_notifications` needs Android "core library
   desugaring." Added `isCoreLibraryDesugaringEnabled = true` + `desugar_jdk_libs` to
   `android/app/build.gradle.kts`. Attempt 9 succeeded.

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundation | DONE | Monorepo scaffolded, all 3 apps boot and were verified live. |
| 1 — Auth + Profile | IN PROGRESS | Backend + mobile screens built and verified. Not built: Google/Apple Sign-In, forgot-password, email verification, settings screen. |
| 2 — Opportunities | IN PROGRESS | Backend + admin web + **mobile screens** all built and verified (real APK build). Missing: internships/graduate-programme sub-tabs (currently reuse the jobs model, spec allows this), career-preferences-driven "recommended" scoring. |
| 3 — ATS | IN PROGRESS | Backend + **mobile screens** (CV upload, analyze, results) built and verified. Missing: CV vault management UI beyond upload/select (rename/set-primary not exposed in mobile UI yet, though the backend supports `is_primary`). |
| 4 — Company Intelligence | IN PROGRESS | Backend + **mobile screens** (feed, detail, company follow, company profile with Jobs/News tabs) built and verified. Admin CMS UI for intelligence posts NOT built (API-only — publish via curl/Postman or extend the Next.js admin app). |
| 5 — Applications | NOT STARTED | |
| 6 — Aptitude Testing | NOT STARTED | |
| 7 — Interview Preparation | NOT STARTED | |
| 8 — Email Tracking | NOT STARTED | |
| 9 — Admin | IN PROGRESS | Jobs/Companies/Scholarships CMS built. Intelligence posts, question bank, source registry, discovery queue, user management NOT STARTED (or API-only). |
| 10 — Monetization | NOT STARTED | `google_mobile_ads` dependency present (bumped to 9.1.0 for Gradle compat) but no ad integration code exists yet. |
| 11 — Production Hardening | NOT STARTED | |

## Completed

### Phase 0/1 (verified previously, still green)
Monorepo scaffold, root docs, backend auth+profile, admin dashboard shell, `docker-compose.yml`
(unverified — no Docker).

### Phase 2 — Opportunities (backend, admin web, AND mobile — all verified)
**Backend/admin** (see prior commit `9593281` for full detail): RBAC foundation, companies/jobs/
scholarships full CRUD with search/filter/save, `expires_at` enforcement, image upload, demo seed data,
Next.js admin CMS for all three, acceptance workflow verified by pytest and by hand.

**Mobile** (`lib/features/jobs/`, `lib/features/scholarships/`, `lib/features/companies/`,
`lib/features/opportunities/`), verified via `flutter analyze`/`test` and a real debug APK build:
- Data layer: hand-written JSON models (`JobCard`/`JobDetail`/`ScholarshipCard`/`ScholarshipDetail`/
  `Company`) matching the backend schemas exactly, repositories wrapping every endpoint built above.
- `OpportunitiesTab` — Jobs/Scholarships sub-tabs (spec §12), each with search, filter chips
  (employment type/work mode for jobs; funding type/degree level for scholarships), infinite-scroll
  pagination, pull-to-refresh, optimistic save/unsave with rollback on failure.
- `JobDetailScreen`/`ScholarshipDetailScreen` — Overview/Requirements-or-Eligibility/Company-or-
  Documents tabs, Save/Analyze CV/Apply action bar, `Apply` opens the real external URL via
  `url_launcher` (never impersonates the employer — spec §14).
- `CompanyDetailScreen` — Overview/Jobs/News tabs, follow/unfollow with optimistic UI.
- `SavedItemsScreen` — Jobs/Scholarships tabs, reachable from Profile → "Saved Jobs & Scholarships".
- **Real bug found and fixed**: `JobListController.toggleSave`/`ScholarshipListController.toggleSave`
  silently no-op when the item isn't already in that controller's own list state — which is exactly
  the case on the detail screen (reached via search, a deep link, or another list) and on the Saved
  Items / company-Jobs-tab screens (items never loaded into the main list controller at all). Fixed by
  having every screen other than the main list call the repository's `save`/`unsave` directly based on
  the item's own `isSaved` field, instead of delegating to a specific list controller's toggle method.

### Phase 3 — ATS (backend AND mobile, verified)
**Backend**: deterministic 8-component weighted scoring engine (`app/matching/ats_engine.py`), real
PDF/DOCX/TXT extraction, synonym normalization, full analyze/history API — see prior commit for detail.

**Mobile** (`lib/features/ats/`): `AtsAnalyzeScreen` — pick/upload a CV (`file_picker`, PDF/DOCX/TXT),
select from previously uploaded CVs, paste a job description (or skip straight to analysis when
reached from a job's "Analyze CV" button, which passes the real job ID). `AtsResultView` — circular
overall-score gauge, full weighted breakdown with per-component progress bars and percentages, strong
matches / missing keywords as colored chips, formatting issues list, missing-quantified-achievements
note — every number traceable to a named component, never a bare percentage (spec Rule 8).
Reachable from a job's detail screen and from Profile → "CVs & ATS Analysis".

### Phase 4 — Company Intelligence (backend AND mobile, verified)
**Backend**: full CRUD news feed with categories, company follow/unfollow, hedged "why this matters"
copy — see prior commit for detail.

**Mobile** (`lib/features/intelligence/`): `IntelligenceFeedTab` — category filter chips + a
"Following" toggle, infinite scroll, pull-to-refresh, honest empty states distinguishing "no news at
all" from "no news from companies you follow yet." `IntelligenceDetailScreen` — headline, content, and
a visually distinct "Why This Matters To Your Career" card showing the admin-written hedged copy plus
relevant roles/skills, with a link to the original source. Company follow surfaced on
`CompanyDetailScreen` (optimistic follow/unfollow button) and reflected on `Company.isFollowing`.

## Partially Complete

- **Mobile app**: Phase 0/1/2/3/4 core loops written and verified. Not yet built: internships/graduate-
  programme-specific mobile UI (data model already supports it via the jobs schema), CV rename/set-
  primary controls, career-preferences-driven personalization anywhere.
- Admin web: no UI yet for intelligence posts (API-only) — jobs/scholarships/companies CMS pattern is
  established and would extend the same way.

## Not Started

- Mobile: Google/Apple Sign-In, forgot-password, email verification, settings, profile-setup wizard
  beyond name/location/experience, aptitude/interview prep screens (Prepare tab is still an honest
  empty state).
- Admin web: intelligence post CMS UI, question bank, source registry, discovery queue, user mgmt.
- Everything under Phases 5–11 (application tracker, aptitude engine, interview prep, email classifier,
  AdMob integration code, production hardening).

## Blocked by Credential / Tooling

- Docker not installed → Postgres/compose stack unverified.
- Google/Apple Sign-In, Gmail/Outlook OAuth, AdMob production IDs, FCM/APNs keys — none supplied;
  provider abstraction + mocks land when those specific phases are reached (spec Rule 3).
- Forgot-password needs a transactional email sender — not chosen/configured.
- iOS build cannot be attempted or verified on this machine at all (Windows, no macOS/Xcode).

## Known Bugs

None currently open. Found and fixed this session (backend + mobile toolchain bugs from the prior
commit still apply — see git log — plus, from the mobile screens pass):
- `AppColors.violet` doesn't exist (the palette constant is `purple`) — `flutter analyze` caught every
  usage across the intelligence screens.
- `file_picker` v12's API changed (`FilePicker.platform.pickFiles(...)` → `FilePicker.pickFile(...)`,
  a static method, no more `.platform` singleton) — caught by `flutter analyze`, not by chance.
- **The save/unsave list-relative-toggle bug described above under Phase 2** — found by reasoning
  through which screens can reach a job/scholarship without it being in `jobListProvider`/
  `scholarshipListProvider`'s state (detail screens via search or deep link, Saved Items, a company's
  Jobs tab), not by a runtime crash — the bug was a silent no-op, not an exception.

## Tests

- Backend: `pytest -q` → **49 passed** (unchanged this pass — no backend code changed while building
  mobile screens).
- Admin: no automated tests — verified by hand via live browser interaction.
- Mobile: `flutter test` → 1 passing smoke test (unchanged — still just the app-boots-to-splash check).
  Widget/unit tests for the new screens are a Next Task; verification so far is `analyze` (type/lint
  correctness) + a full APK build (compiles and packages) + manual reasoning about data flow, not
  automated behavioral tests of the new screens.

## Known issues to revisit

- `npm audit` on `admin/` reports advisories against Next.js 14.2.35 (mostly self-hosted DoS/SSRF/
  cache-poisoning, fixed only as of Next 16) — revisit in Phase 11 or before any non-localhost exposure.
- `ProfileUpdate` can't clear a field to null — `None`/omitted means "leave unchanged."
- Admin web stores its JWT in `localStorage` — fine for local dev, revisit before non-localhost use.
- `ScholarshipRepository.list_public`'s `degree_level` filter does a text-LIKE on the JSON column's
  string form rather than a real JSON containment query — fine at this scale.
- The `recommended` job/scholarship sort is a documented placeholder (featured-first, then newest).
- ATS job-title scoring is a keyword-overlap proxy, not structural CV parsing — documented as such.
- Many `pubspec.yaml` versions are behind latest beyond what was bumped for Gradle-compat — fine.
- No admin CMS UI for intelligence posts yet.
- No mobile widget/unit tests for the new Phase 2/3/4 screens yet — only `analyze` + a real build +
  manual data-flow review have verified them so far, not automated tests.
- Mobile has no automated test coverage proving the save/unsave optimistic-update-with-rollback logic
  actually rolls back correctly on a real API failure (only reasoned through, not tested).

## Next Tasks

1. Commit the mobile Phase 2/3/4 screens (this pass) — currently uncommitted.
2. Widget tests for the new screens, especially the save/unsave flows across all four entry points
   (main list, detail screen, Saved Items, company Jobs tab) given the bug class found this session.
3. Phase 5 (Applications) or whichever phase the user prioritizes next.
4. Admin CMS UI for intelligence posts, to close out Phase 9's remaining gap for what's already built.
