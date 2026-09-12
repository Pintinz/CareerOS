# CareerOS — Project Status

Last updated: 2026-09-12

This file is the single source of truth for build progress. Update it after every phase.

## Git

- Repo initialized 2026-09-12.
- Baseline commit: `9357753e2af2ee9e011abb37259e0112a2da5b84` — "feat: establish CareerOS foundation and
  Phase 1 authentication", tagged `phase-1-baseline`.
- Everything described below (Phase 2, Phase 3, Phase 4-partial, mobile toolchain + APK) is the next
  commit — see Next Tasks.

## Environment notes (read before assuming anything is verified)

- **Flutter SDK: installed** at `C:\flutter` (stable 3.47.4) — was NOT present at session start; the
  whole mobile toolchain below was installed mid-session specifically to unblock verification.
- **Java: installed** — Eclipse Temurin JDK 17 (zip) at `C:\jdk17\jdk-17.0.20.1+1`. A Microsoft OpenJDK
  17 **installer** attempt via winget hung indefinitely (almost certainly a UAC prompt nobody could
  answer non-interactively) and was killed in favor of the no-install zip.
- **Android SDK: installed** at `C:\Android` — cmdline-tools, platform-tools, multiple platform/
  build-tools versions (34, 35, 36 — Gradle auto-installed 35 mid-build when it turned out to need it),
  CMake 3.22.1 (also auto-installed mid-build). Licenses accepted.
- None of the above three are on permanent PATH/env vars — set up per-session via `dev-env.sh`
  (gitignored, machine-specific). See `DEPLOYMENT.md` → "Mobile toolchain setup" for the permanent
  Windows environment-variable equivalent.
- **Docker: still NOT installed.** `docker-compose.yml` is written but never run; backend dev/test uses
  local SQLite (`DATABASE_URL` swaps cleanly to Postgres once available).
- **Python 3.13 and Node.js: available and used**, backend/admin verified live throughout.

## Mobile toolchain verification (done this session) — ALL GREEN

- `flutter doctor -v`: Flutter/Dart ✓, Windows ✓, Android toolchain ✓, Chrome ✓, connected devices ✓.
  Only remaining warning is the Windows desktop C++ toolchain, irrelevant to Android/iOS.
- `flutter pub get`: clean.
- `flutter analyze`: clean (2 real issues found and fixed along the way — see Known Bugs).
- `flutter test`: 1/1 passing.
- `flutter build apk --debug`: **GREEN.** `build/app/outputs/flutter-apk/app-debug.apk` — 175,603,508
  bytes, SHA1 `43c7e62094354b3e4c4de3c865d76b2739c20780` (matches Flutter's own `.sha1` sidecar),
  confirmed a real Android package via `file`. Took **9 attempts** across three unrelated root causes:
  1. **Network flakiness** (attempts 1-3): Maven Central / Gradle Plugin Portal intermittently
     403'd concurrent artifact requests. Confirmed via direct `curl` (works standalone; 2/8 concurrent
     requests to the same URL got real 403s) — this network's egress gets rate-limited under
     concurrent load, which is exactly what Gradle's resolver generates. Each attempt cached more than
     the last. Added `org.gradle.internal.repository.max.tentatives=10` /
     `...initial.backoff=500` to `android/gradle.properties` (Gradle's documented fix for this).
  2. **Outdated plugin versions** (surfaced at attempt 4): `google_mobile_ads` (was `^5.1.0`) and
     `flutter_secure_storage` (was `^9.2.2`) shipped Gradle scripts incompatible with the Gradle 9.3.1
     this Flutter version bundles. Bumped to `^9.1.0` / `^11.1.1`, which cascaded into bumping
     `file_picker` to `^12.3.0` (transitive `win32` conflict). Re-verified `analyze`/`test` clean.
     Attempts 5-7 then worked through the *same* network flakiness recurring on file_picker/
     image_picker/shared_preferences's own dependency trees (only reached once cause 2 stopped
     masking them).
  3. **Missing standard config** (attempt 8): `flutter_local_notifications` needs Android "core
     library desugaring," off by default. Added `isCoreLibraryDesugaringEnabled = true` +
     `desugar_jdk_libs` to `android/app/build.gradle.kts`. Attempt 9 succeeded.
  - Lesson: a `403` from Maven Central during a Flutter build isn't necessarily a real block —
    verify with a direct `curl` first, and if flaky, keep retrying; failures shifting to *new*
    artifacts each time is convergence, not a stuck loop.
- `android/`/`ios/` platform folders generated via `flutter create . --org com.careeros
  --project-name careeros --platforms=android,ios` without touching existing `lib/`/`pubspec.yaml`
  (confirmed via `git status`).
- iOS: cannot be built or verified at all on this machine (Windows, no macOS/Xcode).

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundation | DONE | Monorepo scaffolded, all 3 apps boot and were verified live. |
| 1 — Auth + Profile | IN PROGRESS | Backend + mobile screens built and verified. Not built: Google/Apple Sign-In, forgot-password, email verification, settings screen. |
| 2 — Opportunities | IN PROGRESS | Backend + admin web functionally complete and verified end-to-end. Mobile screens not started — toolchain is now fully verified (including a real APK build), so this is unblocked. |
| 3 — ATS | IN PROGRESS | Backend functionally complete and verified. Mobile screens not started. |
| 4 — Company Intelligence | IN PROGRESS | Backend functionally complete and verified (news feed, categories, company follow). Admin CMS for it not built yet (jobs/scholarships/companies CMS exists; intelligence posts currently admin-manageable only via the API, not a UI). Mobile screens not started. |
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

### Phase 2 — Opportunities (backend + admin web, verified live + by test + by hand)
- RBAC foundation: `admin_users` (separate from `users`), `AdminRole` enum, audience-scoped JWTs
  (`aud: user` vs `aud: admin`, cross-use rejected with 401 — explicitly tested).
- `companies`/`jobs`/`scholarships`: full CRUD, slugs, pagination/search/filters (jobs also filter by
  `company_id`), save/unsave, `GET /me/saved-{jobs,scholarships}`, publish/unpublish/archive/duplicate,
  `is_demo` flagging. `published_at` auto-sets on first publish only. Jobs respect `expires_at` on both
  the list query and the detail/save routes (bug caught and fixed this session).
- Image upload (`POST /admin/uploads/image`) with a swappable local-disk `StorageProvider`.
- Demo seed script (`scripts/seed_demo_data.py`), idempotent, actually run and verified.
- **Acceptance workflow verified twice** — pytest and by hand: admin logs in → creates company →
  creates job/scholarship as DRAFT → confirms invisible publicly → publishes → confirms visible with
  correct data → a user saves it → confirms it persists → unsaves.
- Admin web (Next.js): `/login`, `useAdminGuard`, `/companies`, `/jobs[/new,/[id]]`,
  `/scholarships[/new,/[id]]` — driven by hand in a real browser, which caught a real bug (job form's
  company picker requesting `page_size=200` against a backend cap of 100).

### Phase 3 — ATS (backend, verified)
- `app/matching/ats_engine.py` — deterministic 8-component weighted score (keyword match 25%,
  technical skills 20%, experience 20%, job title 10%, formatting 10%, education 5%, completeness 5%,
  placement 5%). Every result carries the full breakdown, never a bare percentage.
- `app/matching/text_utils.py` — frequency-ranked keyword extraction, years-of-experience heuristic.
- `app/matching/synonyms.py` — explicit synonym table (PLC ↔ "programmable logic controller", HSE,
  DCS, SCADA, P&ID, LOTO, etc. — spec §15's exact examples plus more).
- `app/services/document_extraction.py` — real PDF (pypdf) / DOCX (python-docx) / TXT extraction.
- `POST /ats/cv`, `GET /ats/cv`, `DELETE /ats/cv/{id}`, `POST /ats/analyze`, `GET /ats/analyses`.
- Tests verify: a deliberately strong CV scores higher than a weak one against the same JD; synonym
  normalization causes a match despite different wording; weights sum to 1.0; upload validation;
  analyzing against a real `job_id` pulls that job's actual text.

### Phase 4 — Company Intelligence (backend, verified live + by test)
- `intelligence_posts` — full CRUD (admin), category filter (13 values from spec §19), `company_id`
  optional (industry-wide news isn't always company-specific), `why_it_matters` is admin-written free
  text (never generated — no AI summarizer exists, and spec §20 requires hedged language a human
  commits to).
- `company_follows` — follow/unfollow (`POST`/`DELETE /companies/{id}/follow`), `is_following` on
  company responses, `GET /me/followed-companies`, `?followed_only=true` filter on the intelligence
  feed.
- Verified live via curl (admin publishes → public feed shows it with hedged "why it matters" text
  intact) and by pytest (5 tests: full workflow, category filter, follow+filtered-feed, RBAC, and the
  new jobs `company_id` filter).

## Partially Complete

- **Mobile app**: Phase 0/1 screens written and verified (`flutter analyze`/`test` clean, real debug
  APK builds). Phase 2/3/4 mobile screens (Opportunities, CV upload/ATS results, news feed) not started
  — this is the next real task, now fully unblocked.
- Admin web: no UI yet for intelligence posts (API-only) — jobs/scholarships/companies CMS pattern is
  established and would extend the same way.

## Not Started

- Mobile: Phase 2/3/4 screens, Google/Apple Sign-In, forgot-password, email verification, settings,
  profile-setup wizard beyond name/location/experience.
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

None currently open. Found and fixed this session:
- Nullable `>=` pattern in `api_client.dart` (Dio error mapping) — `flutter analyze` caught it.
- Admin job form's `page_size=200` vs. backend's `le=100` cap — found driving the admin UI by hand.
- Jobs not respecting `expires_at` in either the public list query or the detail/save routes.
- Two Android Gradle-plugin-version incompatibilities (`google_mobile_ads`, `flutter_secure_storage`)
  and one missing Android config (`flutter_local_notifications` core library desugaring) — all found
  and fixed getting the debug APK to build.

## Tests

- Backend: `pytest -q` → **49 passed** across `test_health.py`, `test_auth.py`,
  `test_admin_companies.py`, `test_jobs.py`, `test_scholarships.py`, `test_uploads.py`, `test_ats.py`,
  `test_intelligence.py`.
- Admin: no automated tests — verified by hand via live browser interaction.
- Mobile: `flutter test` → 1 passing smoke test. Deeper widget/unit tests are a Next Task.

## Known issues to revisit

- `npm audit` on `admin/` reports advisories against Next.js 14.2.35 (mostly self-hosted DoS/SSRF/
  cache-poisoning, fixed only as of Next 16) — revisit in Phase 11 or before any non-localhost exposure.
- `ProfileUpdate` can't clear a field to null — `None`/omitted means "leave unchanged."
- Admin web stores its JWT in `localStorage` — fine for local dev, revisit (httpOnly cookie + refresh
  rotation) before any non-localhost deployment.
- `ScholarshipRepository.list_public`'s `degree_level` filter does a text-LIKE on the JSON column's
  string form rather than a real JSON containment query — fine at this scale, revisit with Postgres
  JSONB `@>` once volume matters.
- The `recommended` job/scholarship sort is a documented placeholder (featured-first, then newest),
  not the real matching engine (needs a user profile to score against).
- ATS job-title scoring is a keyword-overlap proxy against the whole CV text, not structural parsing
  of "candidate's most recent title" — documented as a simplification in `ats_engine.py`.
- Many `pubspec.yaml` versions are behind their latest (see `flutter pub outdated`) beyond the three
  bumped for Gradle-compat reasons — fine, not urgent, but don't assume everything is current.
- No admin CMS UI for intelligence posts yet — publish via the API directly (or extend the Next.js
  admin app following the jobs/scholarships pattern) until that UI is built.

## Next Tasks

1. Commit everything above (Phase 2/3/4 backend/admin, mobile toolchain fixes, `android/`/`ios/`
   scaffolding, the built APK is gitignored build output — don't commit the .apk itself).
2. Build mobile Phase 2/3/4 screens: Opportunities (Jobs/Scholarships), CV upload + ATS results,
   company intelligence feed — wired to the now fully-verified backend, buildable to a real APK.
3. Admin CMS UI for intelligence posts (follow the jobs/scholarships pattern already established).
4. Then: Phase 5 (Applications) — whichever the user prioritizes.
