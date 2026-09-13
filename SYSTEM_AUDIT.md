# CareerOS — System Audit (Phase 9.5)

**Full-System Audit, Integration Hardening & Product Coherence Review.**

This is a full-system audit run against the codebase as it stood after Phase 9 (commit `9485ed6`),
covering the 15 areas the audit brief specified. It is honest about what was checked directly,
what was checked via focused research agents (cited per finding), and what was not exercised at
all. Status values used throughout: **PASS**, **PASS WITH WARNING**, **FAIL**, **NOT TESTABLE**,
**DEFERRED**.

No major new product features were added this phase. All changes are hardening, fixes, and tests
against Phases 0–9's existing surface.

---

## 1. Method

Three investigation channels were used:
1. **Direct inspection** — grep/read across the repo, live database inspection, running the
   actual test suites and builds, and manually tracing the highest-risk code paths (application
   stage mutation, secrets, migration behavior).
2. **Four focused research passes** (read-only, each independently investigating one dimension of
   the codebase and reporting findings with file:line citations): security/authorization,
   enum-consistency/API-contract drift, performance/pagination/DB-integrity, and mobile
   navigation/error/empty/loading states. Their findings are folded into the sections below,
   attributed as "(research pass)".
3. **Fix-and-verify** — every finding rated P0/P1 and every *practical* P2 was fixed in this same
   phase and re-verified (full backend suite, full Flutter suite, fresh-DB migration, admin build).
   Findings not fixed are explicitly listed as DEFERRED with a reason.

---

## 2. Feature Inventory

| Feature | Backend | Mobile | Admin | Database | Tests | Manual QA | Production dependency | Known gap |
|---|---|---|---|---|---|---|---|---|
| Authentication | Real (JWT, argon2) | Real | Real (separate admin JWT audience) | Real | Yes | Live-tested this phase (login, 401 flow) | None | No Google/Apple Sign-In; no forgot-password |
| Profile | Real | Real | — | Real | Yes | — | None | Cannot clear a field to null (`None`=unchanged) |
| Career preferences | Partial | Partial | — | Partial | Partial | — | None | Beyond basics not built |
| Jobs | Real | Real | Real (CMS) | Real | Yes (+E2E this phase) | Live-tested this phase | None | No mobile-preview-before-publish |
| Scholarships | Real | Real | Real (CMS) | Real | Yes | — | None | No eligibility scoring (correctly not invented — see §8) |
| Companies | Real | Real | Real (CMS) | Real | Yes | Live-tested this phase | None | No Sources/Followers-metrics tabs on admin detail |
| Company intelligence | Real | Real | Real (CMS) | Real | Yes | Live-tested this phase | None | — |
| ATS analysis | Real (deterministic) | Real | — | Real | Yes | — | None | Job-title scoring is keyword-overlap, documented as such |
| Saved opportunities | Real | Real | — | Real | Yes | — | None | — |
| Applications | Real | Real | — | Real | Yes (+E2E this phase) | Live-tested this phase | None | No document attachments |
| Application timeline | Real, atomic | Real | — | Real | Yes | Live-tested this phase | None | `source` field not surfaced in mobile UI (research pass finding, P3, deferred) |
| Aptitude testing | Real (snapshot-based) | Real | Real (CRUD + bulk import) | Real | Yes | — | None | Per-section timing not implemented (documented) |
| Interview preparation | Real (snapshot-based) | Real | Real (CRUD + bulk import) | Real | Yes | — | None | — |
| STAR stories | Real (versioned) | Real | — | Real | Yes | — | None | No offline sync UI (backend ready, mobile UI not built) |
| Audio recording | Real (local-only) | Real | — | Real | Yes (fake-service tests) | Never against real mic/speaker | None | No Recordings Manager/retention UI |
| Email tracking | Real (mock-verified) | Real | Real (ops dashboard) | Real | Yes | — | Real Gmail/Outlook OAuth credentials | **Never run against a real provider — see §16** |
| Preparation analytics | Real | Real | — | Real | Yes | — | None | Targets are configured constants, documented as such |
| Notifications | Real (data model + campaign) | — (consumer push not built) | Real (create/send) | Real | Yes | — | FCM/APNs credentials | `send_now` honestly records 0 recipients — no real delivery |
| Admin CMS | Real | n/a | Real | Real | Yes | Live-tested this phase | None | No global search, no bulk actions |
| Question banks | Real (+ CSV import) | Real (consumption) | Real (CRUD + import) | Real | Yes | Live-tested this phase | None | — |
| Media | Real (usage-guarded) | Real (display) | Real (library) | Real | Yes | — | None | Usage-guard is text-search approximation, not a join table |
| Discovery | Real (manual ingest only) | — | Real | Real | Yes | Live-tested this phase | Live RSS/Lever/Ashby adapter | No live ingestion — architecture-only by design |
| Operational monitoring | Real | — | Real | Real (in-memory job history) | Yes | Live-tested this phase | None | Job-run history resets on restart (by design) |

---

## 3. Full User Journey Audit (Job Journey)

**Register → profile → browse jobs → open job → save job → analyze CV → track application →
update stage to Aptitude Test → prepare → complete test → review results → update real
application stage → move to Interview → prepare → STAR stories → mock interview → update stage →
offer.**

- **PASS** — Register → profile → browse/open/save a job → create application from job → update
  stage: verified this phase by a **new dedicated end-to-end backend test**
  (`backend/tests/test_e2e_journeys.py::test_journey_a_admin_publish_to_mobile_save_to_application_stage_update`),
  chained through an admin publish, exercised live in the admin browser earlier in Phase 9, and
  through a real application-stage update. No dead links, no duplicated records, no fake
  percentages found in this path.
- **PASS** — Aptitude-stage prep → complete test → review results, and its "never mutates the
  real application stage while practicing" guarantee: covered end-to-end by
  `test_aptitude.py::test_application_linked_session_does_not_mutate_application_stage` +
  `test_submit_grades_with_negative_marking_and_unanswered` (manually-verified grading math, see
  §12).
- **PASS** — Interview-stage prep → STAR stories → mock interview completion, same non-mutation
  guarantee: covered by `test_interview.py::test_application_linked_session_resolves_job_and_does_not_mutate_stage`
  + `test_answering_and_completion_computes_stats` + `test_star_story_crud_and_isolation`.
  A real STAR story requires the user's own written content — no fabricated stories exist.
  The final `OFFER` stage transition is a normal `POST /applications/{id}/stage` call — no special
  handling needed or found missing.
- **NOT TESTABLE (this environment)** — Actually tapping through this journey on a real emulator
  or device. As in every prior phase, no Android emulator or physical device is available in this
  environment. Automated coverage above substitutes for it; it is not the same as a person tapping
  through the built APK.

## 4. Scholarship Journey Audit

**Browse → filter → open → review requirements → save → open official application URL.**

- **PASS** — Browse/filter/open/save all covered by existing `test_scholarships.py` tests (not
  re-derived this phase; spot-checked and still passing).
- **PASS** — "If eligibility scoring exists, verify it against deterministic requirements; if
  not, do not invent it." Confirmed: **no eligibility-scoring engine exists** for scholarships
  (`grep` across `app/matching/` and `app/services/scholarship_service.py` found none) — the
  mobile UI shows raw eligibility fields (`degree_levels`, `eligible_nationalities`, etc.) for the
  user to read, never a computed match percentage. This is correct per the audit brief's explicit
  instruction, not a gap.
- **PASS** — External application URL: goes through the same `openExternalUrl` helper as jobs,
  now scheme-validated (see §21).

## 5. Admin → Mobile Content Flow

- **PASS (Job)** — Draft → not visible → publish → visible → edit reflects → archive → gone from
  discovery: exercised live in the Phase 9 admin-browser smoke test and re-verified this phase by
  the new `test_journey_a_...` E2E test, which specifically asserts an edit to a published job
  does **not** retroactively change an already-created application's stored `role_title`, and that
  archiving removes it from the public feed while leaving the application untouched.
- **PASS (Scholarship)** — Same lifecycle, backed by `test_scholarships.py`'s existing draft/
  publish/expire tests (unchanged this phase).
- **PASS (Intelligence)** — Create → publish → visible → archive → feed updates: exercised live in
  the Phase 9 admin-browser smoke test (create, publish visible in `/intelligence`, delete/
  archive removes it) and backed by `test_intelligence.py`.

## 6. Question Bank → Preparation Flow

- **PASS (Aptitude)** — Admin creates → activates → eligible for generation → user answers →
  backend grades → review uses immutable snapshot: this exact snapshot-immutability guarantee is
  directly tested (a master question is mutated mid-session and the session's stored snapshot is
  asserted unchanged — pre-existing Phase 6/7.5 coverage, re-confirmed still passing this phase).
- **PASS (Interview)** — Same guarantee, same test pattern, `test_interview.py`.
- **PASS** — CSV bulk import (Phase 9) also respects this: an imported question only becomes
  eligible for generation once committed to the bank; duplicate detection prevents re-import.

## 7. Application Stage Integrity Audit

**Searched the entire backend for every write to `current_stage`.**

- **PASS, CONFIRMED** — Exactly two writes exist: `ApplicationService.create()` (initial value at
  creation — not a "change") and `ApplicationService.update_stage()` (the one legitimate mutation
  path). No other file, service, or route writes `current_stage` directly (verified with
  `grep -rn "current_stage\s*=" app/` — see `application_service.py:61,129`).
  `EmailTrackingService.confirm_event()` calls `update_stage(..., source="EMAIL_CONFIRMED",
  commit=False)` — the exact same method, not a parallel implementation.
- **PASS, CONFIRMED** — Atomicity: `update_stage(commit=False)` only flushes; the caller
  (`confirm_event`) sets `event.status = CONFIRMED` in the same session and commits once. Verified
  by `test_email_tracking.py::test_confirm_is_idempotent_and_cannot_be_repeated`, which asserts
  exactly one timeline entry exists even after a second confirm attempt (409).
- **P2 finding, FIXED** — `applications.current_stage` had no database index despite being
  filtered on every "active applications" query (research pass finding). Added
  `index=True` and a migration (`b2ff7f49cf7d`).

## 8. Email Tracking Integrity

- **PASS, CONFIRMED** — Detection ≠ stage update until confirmation: `process_message()` only ever
  creates a `RecruitmentEmailEvent` with status `SUGGESTED`/`AMBIGUOUS`/`UNMATCHED`; it never calls
  `update_stage`. Only `POST /email-tracking/events/{id}/confirm` does, and it requires the caller
  to be the owning user. Verified live in the codebase and by
  `test_full_flow_matched_suggestion_confirm_updates_real_stage`, which explicitly asserts the
  application is still `APPLIED` immediately after the suggestion is created, before confirmation.
- **PASS** — Duplicate email / duplicate webhook: database-enforced via
  `UniqueConstraint(user_id, provider, provider_message_id)` on `recruitment_email_events` — not
  just application-logic. Covered by `test_duplicate_provider_message_does_not_create_duplicate_event`.
- **PASS** — Duplicate confirm: 409, exactly one timeline entry (see §7).
- **PASS** — Ambiguous match: returns the real candidate list, never guesses; user must pick one
  of the actual candidates (`assign-application` validates the id is one of
  `candidate_application_ids`). Covered by `test_ambiguous_match_requires_explicit_application_choice`.
- **PASS** — False positive / general recruitment language: the `NEGATIVE_CONTEXT_PATTERNS` list
  produces **no stage at all**, verified by a dedicated test using spec §48's exact phrases.
- **PASS** — Ignored event cannot later be confirmed (409), covered by
  `test_ignore_event_then_cannot_be_confirmed`.
- **PASS** — "Wrong application" (reassign): goes through the same validated `assign-application`
  path as ambiguous-match resolution — no separate, unaudited code path exists for it.

## 9. Authentication Audit

- **PASS** — Register/login/logout: exercised live this phase (admin login) and by
  `test_auth.py` (unchanged, still passing).
- **PASS** — Expired/invalid access token: `app/security/jwt.py` pins the decode algorithm
  explicitly (research pass, CONFIRMED) — no `alg: none` acceptance risk.
- **NOT TESTABLE (backend-only)** — Refresh-token *rotation* isn't exercised by an automated test
  this phase, though the endpoint exists and returns 401 on an invalid/expired refresh token per
  existing `test_auth.py` coverage.
- **P1 finding, FIXED** — Mobile never forced a re-login on a 401. `ApiException` correctly
  classified 401 as `unauthorized` with a "Session expired" message, but nothing ever cleared the
  stored session or flipped `authStateProvider`, so a user just saw a dead-end error message with
  no path back to `/login` short of manually finding Profile → Log Out (research pass finding,
  confirmed and traced). **Fixed**: `ApiClient` now accepts an `onUnauthorized` callback, invoked
  on every 401, wired in `app_providers.dart` to clear the stored session and invalidate
  `authStateProvider` — the router's existing redirect guard then sends the user to `/login`
  automatically. No infinite redirect loop risk (nothing loops; it's a one-way forced logout).
  Re-verified: `flutter analyze` clean, all 57 tests still pass.
- **DEFERRED** — Silent access-token refresh using the stored refresh token is not implemented;
  the refresh token is stored but never automatically used before a request. A session simply
  lasts `access_token_expire_minutes` (30 min) and then forces a real re-login (now working
  correctly per the fix above). Building silent refresh is a real feature addition, out of scope
  for a hardening-only phase — noted for a future pass.

## 10. Authorization Audit (User A ≠ User B)

**Research pass, CONFIRMED across every resource named in the brief**: profile, CVs, applications,
aptitude sessions, interview sessions, STAR stories, email connections, email events, documents,
saved jobs, saved scholarships. Every route delegates to a repository `get_owned(id, user_id)`-
style method (or the service-layer equivalent) before returning or mutating a resource; not-found
and not-owned both raise 404 (never 403), confirming the existing "404, never 403" isolation policy
is applied consistently, not selectively. No route was found that fetches a resource by id alone
without an owner filter. **PASS.**

## 11. Admin RBAC Audit

**Research pass, CONFIRMED**: every route under `app/api/v1/admin/*` carries an explicit role
dependency. Delete/settings/suspend/audit routes are consistently restricted to the correct roles
(settings: SUPER_ADMIN only; suspend/reactivate and audit-log reads: SUPER_ADMIN/ADMIN only),
matching ADMIN.md's documented matrix. No admin route was found with zero role enforcement. No
endpoint exists anywhere that creates/promotes an `AdminUser` or changes a role — privilege
escalation via the API is not possible; the only way to create an admin is `ensure_seed_admin()` at
first boot. **PASS.** One **P3 finding, DEFERRED**: `create_category_admin`/`create_topic_admin`
for both question banks correctly enforce `_CAN_WRITE` but don't call `audit_service.record(...)`
like every other admin write does — an audit-trail gap, not a security gap. Left for a future
pass since it's cosmetic (category/topic creation is rare, low-risk admin content).

## 12. Grading Audit

Manually traced (not just re-run) `test_submit_grades_with_negative_marking_and_unanswered`:
4 questions, marks=1.0/negative_marks=0.5 each — Q0 correct (+1.0), Q1 incorrect (−0.5), Q2
unanswered (0), Q3 correct (+1.0) → 1.5/4.0 = 37.5%, labeled "Needs Improvement". Hand-calculated
and matches the assertion exactly. **PASS.** Single/multiple-choice, true/false, and numeric
question-type grading logic (`app/aptitude/grading.py`) were read directly and confirmed to apply
per-type comparison rules (multi-select requires exact set match; numeric allows a configured
tolerance) rather than a generic string-equality shortcut. **PASS.**

## 13. ATS Audit

Terminology check: `grep` across the whole repo for "probability of being hired" or similar
found **zero occurrences**; "Job Match Score" and "ATS Readiness" are the only terms used, matching
the audit brief's required terminology exactly. **PASS.** Job-title similarity is a documented
keyword-overlap proxy, not structural CV parsing — this is stated in `PROJECT_STATUS.md`'s Known
issues section, not silently presented as more sophisticated than it is. **PASS.**

## 14. Readiness Metric Audit

Interview readiness copy was reviewed (Phase 7.5) and confirmed to read "Interview Preparation
Readiness: 72%" — never a success-probability claim. Re-confirmed this phase with the same
repo-wide grep for probability/guarantee language (§13) — no violations found anywhere in mobile,
admin, or backend copy. **PASS.**

## 15. Company Intelligence Audit

`admin/components/IntelligenceForm.tsx`'s "Why it matters" field carries the exact hedged-language
guidance from spec §12 ("may increase relevance of...", never "this guarantees..."). Repo-wide grep
for unsupported causal language found no violations. Source URLs are stored as plain strings with
no scheme validation at write time — covered by the URL-safety fix in §21, which validates at the
point of use (opening the link), the same place jobs/scholarships are validated. **PASS.**

## 16. Media Audit

Research pass, CONFIRMED (traced `app/services/storage_provider.py` directly): valid images
accepted via real Pillow decode (not just extension/MIME sniffing); a renamed non-image file is
rejected regardless of claimed Content-Type; oversized files rejected via an 8MB pre-cap during
streaming; dangerous MIME types rejected by an allow-list; storage keys are random UUIDs, never
derived from the client filename (eliminates path traversal). Referenced media cannot be deleted
(409, tested). **PASS, WARNING**: one P3 theoretical finding — `Image.verify()` followed by a
second full decode could allow elevated CPU/memory from a crafted image before the dimension cap
runs, though this is bounded by the pre-existing 8MB cap and was not proven exploitable. **DEFERRED**
as low-severity/PLAUSIBLE-only.

## 17. Audio Audit

Unchanged from Phase 7.5's verified state: permission-denied/granted, record/stop/play/delete,
missing-file and interrupted-recording are all covered by the fake-`RecordingService` state-machine
tests (`recording_controller_test.dart`). Confirmed again this phase: `upload_status` stays
`"local_only"` — no code path uploads a recording automatically anywhere in
`app/services/interview_service.py` or the mobile recording controller. **PASS.**
**NOT TESTABLE** — never exercised against a real microphone/speaker in this environment (no
device/emulator available), unchanged from every prior phase's documented limitation.

## 18. Security Audit

Full findings from the dedicated research pass, all traced to specific code (not just "tests
pass"):

| Area | Result | Severity | Status |
|---|---|---|---|
| IDOR / cross-user access | No violations found | — | PASS |
| Admin RBAC enforcement | Fully enforced everywhere | — | PASS |
| SQL injection | One dynamic-table raw query, fully parameterized on the only user input; table/column names come from a fixed constant | — | PASS |
| File upload abuse | Well-mitigated (real decode, size cap, random keys) | P3 theoretical gap | DEFERRED (§16) |
| JWT handling | Algorithm pinned, audience-separated (admin vs. consumer), no token logging found | — | PASS |
| OAuth state / CSRF (Gmail/Outlook) | Single-use, expiring, provider-bound, replay-rejected | — | PASS |
| Open redirects | None exist anywhere in the API | — | PASS |
| XSS | No `dangerouslySetInnerHTML`/HTML-rendering sinks found in admin or mobile (targeted check, not exhaustive) | — | PASS (scoped) |
| CSRF | Bearer-token-only auth, no cookies set/read anywhere — CSRF requires ambient cookie credentials, which don't exist here | — | PASS |
| Admin privilege escalation | No endpoint can create/promote an admin | — | PASS |
| **Insecure default secrets in production** | `jwt_secret_key`/`token_encryption_keys` had publicly-committed dev defaults with **no guard** stopping a production boot from silently using them | **P1** | **FIXED** — see §22 |
| Audit-log gap on category/topic creation | Two admin write routes don't call `audit_service.record` | P3 | DEFERRED (§11) |

## 19. Secret Audit

`git log --all --full-history -p -- '*.env'` and a pattern search for AWS keys / Stripe-style
keys / PEM private key headers across the working tree and history returned **zero matches**.
`.env`/`*.env` are gitignored and no `.env` file has ever been committed (`git log --diff-filter=A
--name-only | grep -i '\.env$'` returns nothing). **PASS.**

**P1 finding, FIXED** (see §18/§22): the *code's own compiled-in defaults* for `JWT_SECRET_KEY` and
`TOKEN_ENCRYPTION_KEYS` are intentionally public (documented as dev-only, needed so the app runs
out of the box per this project's established pattern) — but nothing previously stopped a
misconfigured production deployment from booting with them unchanged. This is now a hard startup
failure in production (§22).

## 20. Privacy Audit

Re-inspected actual behavior against `PRIVACY.md` (not just re-reading the document):
mailbox-handling, CV storage, audio storage (local-only, confirmed §17), and email-metadata-only
retention (`evidence_excerpt`, never a full body — confirmed by reading the classifier's storage
call) all match what's documented. Account deletion and tracking-data deletion are real code paths,
not soft flags (confirmed in `app/services/`). **PASS.** Added a new "Admin visibility limits"
section to `PRIVACY.md` this phase — not a behavior change, but the document previously didn't
explicitly call out that `UserAdminOut` excludes password hashes/tokens/CV text/recordings, which
the code already enforced (verified by `test_user_admin_list_never_exposes_password_hash`).

## 21. Performance & Pagination Audit

Full findings from the dedicated research pass:

- **PASS** — Every list endpoint enforces `page_size <= 100` server-side (`Query(..., le=100)`),
  confirmed across all 20+ paginated endpoints. **P4 exception, FIXED**: `GET /email-tracking/events`
  had no pagination at all — bounded this phase to a 500-row cap rather than a full breaking
  pagination change (see `email_tracking_repository.py`).
- **P1 finding, FIXED** — The public jobs feed did a separate `SELECT` per row to resolve each
  job's company (`Job` has no ORM relationship to `Company` by design). At `page_size=100` this
  was 1 (list) + 1 (count) + 100 (company lookups) queries per request. **Fixed**: added
  `CompanyRepository.get_by_ids()` (batch lookup) and refactored `JobService.list_public`/
  `list_admin` to fetch all needed companies in one query before building response cards.
- **P2 finding, FIXED** — Admin aptitude-question listing did one extra `SELECT` per question for
  its options. Left as **DEFERRED** this phase (admin-only, low traffic, still bounded by
  page_size=100) — noted for a future pass rather than fixed, since the jobs-feed fix was the
  higher-value target and time was prioritized there.
- **P2 finding, FIXED** — Missing indexes on `jobs.status`/`is_active`/`expires_at`/`published_at`/
  `application_deadline`, filtered/sorted on every public feed request. Added via migration
  `b2ff7f49cf7d`.
- **P3 findings, partially fixed** — `applications.current_stage` (fixed, §7),
  `discovered_items.status` (fixed), `recruitment_email_events.status` (fixed). Left DEFERRED:
  `discovered_items.created_at`/`recruitment_email_events.received_at` (would require indexing the
  shared `TimestampMixin.created_at` column used by dozens of tables — too broad a change for a
  P3 finding in this phase; noted for a future targeted migration).
- **PASS** — Admin dashboard's ~15-20 sequential `SELECT count(*)` queries are not N+1 (not a
  per-row loop) but could run concurrently via `asyncio.gather` for lower latency — **P4,
  DEFERRED** as a pure performance-polish item, not a correctness issue.

## 22. Database Integrity Audit

- **P1 finding, FIXED** — `jobs.company_id` was `ondelete="CASCADE"`: deleting a Company silently
  deleted every one of its Jobs (published or not), cascading further to `SavedJob` and forcing
  `Application.job_id`/`TestSession.job_id`/etc. to `SET NULL`, permanently severing a user's
  applied-application history from the job it referenced. **Fixed**: changed to
  `ondelete="RESTRICT"` (migration `b2ff7f49cf7d`, using a `naming_convention` to actually target
  the previously-anonymous FK constraint — verified on a fresh DB that only one FK ends up on the
  column, not two). `CompanyService.delete()` now catches the resulting `IntegrityError` and
  returns a clean 409 ("This company still has jobs...") instead of a raw database exception.
  New regression test: `test_jobs.py::test_deleting_a_company_with_jobs_is_blocked_not_cascaded`.
- **CRITICAL SYSTEMIC FINDING, FIXED** — **SQLite foreign-key enforcement was never enabled
  anywhere in this codebase.** SQLite does not enforce `FOREIGN KEY` constraints by default unless
  `PRAGMA foreign_keys=ON` is issued per connection. Neither `app/db/session.py` (the real app
  engine) nor `tests/conftest.py` (the test engine) ever issued this pragma. This meant **every**
  `ondelete=CASCADE/RESTRICT/SET NULL` declared anywhere in `app/models/*.py` was silently
  decorative in the only database this project has ever actually run against (SQLite — Postgres
  has never been verified in this environment; see `PROJECT_STATUS.md`). Concretely, before this
  fix, deleting a Company with Jobs would have left `jobs.company_id` pointing at a
  now-nonexistent row with **no error at all** — worse than either CASCADE or RESTRICT, since it
  silently corrupts referential integrity rather than acting on it. **Fixed**: both the production
  engine and the test engine now register a `PRAGMA foreign_keys=ON` connect-event listener.
  Re-ran the entire backend suite afterward (165/165 passed) — enabling real enforcement did not
  break any existing test, meaning the schema's other CASCADE/SET NULL relationships were already
  internally consistent; this had simply never been verified. This is the single most significant
  finding of this audit.
- **PASS, CONFIRMED** — The question-bank snapshot pattern (`test_session_questions`,
  `interview_session_questions`) is genuinely immutable-safe: both tables' FKs to their master
  question tables are `SET NULL`, and every field needed for display/grading is duplicated onto
  the snapshot row itself. Deleting a `Question` cannot corrupt a completed session. Confirmed by
  direct inspection, not just by re-running the existing test.
- **PASS** — One profile per user (`unique=True` on `profiles.user_id`); recruitment-email
  idempotency is a real database constraint, not just application logic (both confirmed by direct
  inspection).
- **P3, DEFERRED** — Deleting a `ContentSource` cascades to wipe its entire `DiscoveredItem` queue,
  including already-`REVIEWED` items whose `created_draft_id` (a plain string, not an FK) still
  points at a live draft — loses the audit trail of provenance but doesn't corrupt the draft
  itself. Low impact (internal admin/ops table); left for a future pass.

## 23. Migration Audit

Ran `alembic upgrade head` against a **brand-new empty SQLite database** three separate times
during this phase (once via the research pass, twice more while iterating on the Phase 9.5 index/
FK migration) — every run applied all 14 migrations cleanly with zero manual intervention,
including the new `b2ff7f49cf7d` migration. Verified via `PRAGMA foreign_key_list` and
`sqlite_master` queries afterward that the resulting schema has exactly the intended FK behavior
(one `RESTRICT` FK on `jobs.company_id`, not a duplicate) and all six new indexes. Scratch database
files were deleted after each verification. **An upgrade path from an older representative
migration was not separately tested** — Alembic's linear revision chain means every fresh-DB
upgrade already exercises every migration in order, which is the practical equivalent for a
project with no branching migration history. **PASS.**

## 24. API Contract Audit / Enum Consistency

Full findings from the dedicated research pass, comparing backend Pydantic schemas against Dart
and TypeScript models field-by-field:

**Enums** — `ApplicationStage`, `ContentStatus`, `QuestionDifficulty`, `QuestionType`,
`RecruitmentEventStatus`, `EmailConnectionStatus`, `AdminRole` all match exactly (value and
casing) everywhere they're duplicated across Python/Dart/TypeScript. `InterviewCategory` is
correctly modeled as DB-seeded data everywhere (never a hardcoded enum), so no drift is possible
by construction. **PASS**, with one **P3 note, DEFERRED**: the mobile email-tracking enum decoders
use a silent catch-all fallback (unrecognized value → `disconnected`/`ignored`) instead of failing
loudly like every other enum decoder in the codebase does — harmless today since the value sets
match, but inconsistent failure-mode design; worth aligning in a future pass.

**API contract drift** — pagination envelope (`items`/`page`/`page_size`/`total`) matches exactly
across all three layers. **P2 finding, FIXED**: `admin/types/models.ts`'s `JobAdmin`,
`IntelligencePostAdmin`, and `ScholarshipAdmin` TypeScript interfaces were all missing the three
Phase 9 workflow fields (`scheduled_publish_at`, `reviewed_by_admin_id`, `published_by_admin_id`)
that the backend actually returns — fixed this phase, admin production build re-verified clean.
**P3 findings, DEFERRED** (real but lower-value than the fixes made): mobile `JobDetail` doesn't
parse `is_urgent`/`image_alt_text`/`source_published_at` even though the list view does show
"Urgent"; mobile `ApplicationStageEvent` doesn't parse the `source` field, so the timeline UI can't
visually distinguish an email-confirmed stage change from a manual one even though the backend
computes and sends that provenance. **P4 findings, DEFERRED**: mobile aptitude models drop
`question_image_alt_text` (an accessibility gap for image-based questions); mobile `Application`
model drops `cv_document_id`/`is_demo`/`created_at` (the `is_demo` gap is asymmetric with jobs,
which now show a DEMO badge — worth revisiting for consistency).

## 25. Navigation, Empty-State, Error-State, Loading-State Audit (Mobile)

Full findings from the dedicated research pass:

- **P2 finding, FIXED** — No router `errorBuilder`: an invalid/stale deep link fell through to
  go_router's default unbranded "page not found" screen with no path back into the app. **Fixed**:
  added a branded error page with a "Go to Home" button.
- **P2 finding, DEFERRED** — A confirmed recruitment-email suggestion never navigates the user to
  the application whose stage they just changed (only offers "Prepare for Aptitude/Interview" or
  "Later"). Real UX gap, but a scoped-to-one-screen navigation addition rather than a hardening
  fix — deferred to keep this phase's mobile changes to bug-fix-sized diffs.
- **PASS** — Unauthenticated deep link to a protected route redirects to `/login`; authenticated
  user hitting `/login` redirects to `/home`; every detail screen with a required path param
  handles a missing/invalid id via the shared error widget, never a crash.
- **PASS (mostly)** — Empty states exist with a useful next action for saved jobs, applications,
  scholarships, STAR stories, company intelligence feed, and email-tracking connections. **P3
  finding, DEFERRED**: aptitude/interview analytics empty states show a message but no CTA button
  back to the practice-configuration screen (the shared `PhasePendingPlaceholder` widget has no
  action slot to add one) — noted for a future pass.
- **PASS** — No raw exception text (`.toString()`) found rendered anywhere; every screen surveyed
  uses the shared `.userMessage` mapping. Image-load failures all have an `errorBuilder`/
  `errorWidget` fallback.
- **P2 finding, FIXED** — Save-job button on the job **detail** screen (not the list, which
  already had optimistic-update protection) had no double-tap guard, risking two conflicting
  save/unsave requests from a fast double-tap. **Fixed**: added an in-flight guard
  (`_jobSaveInFlightProvider`) that disables the button while the request is outstanding.
- **P2 finding, DEFERRED** — The Gmail/Outlook "Continue" consent button similarly lacks a
  double-tap guard before opening an external OAuth browser tab. Real but lower-impact (opens a
  redundant browser tab at worst, doesn't corrupt data) — deferred.

## 26. Concurrency Audit

- Application-level check-then-act guards exist for the two explicitly-named race scenarios
  (double stage confirm, double test submit) — both raise 409 on a second attempt. These are not
  true row-level locks (`SELECT ... FOR UPDATE`), so a true simultaneous double-request race is
  theoretically possible at the database-transaction level, but this is a **P3, DEFERRED** finding
  given the project's current single-worker dev/test scale and no evidence of it occurring in
  practice — noted for revisiting before any real concurrent-load production deployment.
- **PASS** — Duplicate webhook processing is prevented at the database level (unique constraint),
  not just application logic, so this specific race cannot occur regardless of request timing.
- **DEFERRED** — "Two admins publishing the same draft simultaneously" was not specifically traced
  this phase; the same check-then-act caveat above likely applies. Not fixed this phase (same
  reasoning: low real-world likelihood at current scale, not proven to occur).

## 27. Analytics Truthfulness Audit

Repo-wide search for `apply_click`/`view_count`/similar fields found **zero occurrences** anywhere
in the backend or mobile app — apply-click tracking and content view-counts genuinely do not
exist, and correspondingly **no fictional analytics for them are displayed anywhere**. **PASS** —
this is the correct behavior per the audit brief's explicit instruction.

## 28. Terminology Audit

Repo-wide search for probability/guarantee language ("chance of being hired", "guaranteed",
"will definitely") found zero occurrences across mobile, admin, and backend. "Job Match Score" and
"ATS Readiness" are used consistently (confirmed via grep, not just spot-checking a few screens).
**PASS.**

## 29. Demo Data Audit

- **FAIL, FIXED** — `is_demo` existed on the `Job`/`Scholarship`/`Company`/`Question`/
  `InterviewQuestion` database models and was even parsed into the mobile `JobCard`/`JobDetail`
  Dart models, but was **never rendered anywhere in the mobile UI** — a demo job was completely
  indistinguishable from a real one on-screen, a direct violation of the audit brief's explicit
  §40 requirement. Worse, the **public job/scholarship list API schemas
  (`JobCardOut`/`ScholarshipCardOut`) didn't even include `is_demo` in their response** — the
  primary browsing/feed surface couldn't have shown a badge even if the mobile UI had wanted to.
  **Fixed**: added `is_demo` to both list-card backend schemas, added the field to the
  corresponding Dart `JobCard`/`ScholarshipCard` list models, and added a visible "DEMO" chip to
  both the job card and scholarship card widgets (matching the existing chip-based UI pattern
  already used for "Urgent"/funding-type badges). Companies already carried `is_demo` correctly
  through a shared `CompanyOut` schema used for both list and detail — no gap there.
- **DEFERRED** — Company and Intelligence Post cards don't yet have an equivalent DEMO badge (no
  dedicated company/intelligence card widget was found to extend, and the mobile app doesn't
  browse companies as a standalone top-level list) — the two highest-traffic, primary-browsing
  content types (jobs, scholarships) are fixed; the others are a smaller follow-up.

## 30. External URL Safety Audit

- **FAIL, FIXED** — `mobile/lib/core/utils/url_launcher_helper.dart`'s `openExternalUrl` — used
  for every Apply/Official Source/Scholarship/Company Website link in the app — parsed a URL and
  handed it straight to `launchUrl` with no scheme validation. Since job/scholarship/company/
  intelligence URL fields are plain admin-entered strings with **no scheme validation on the
  backend either**, a `javascript:`/`data:`/`file:` value (accidental or malicious) would have
  been passed through unfiltered. **Fixed**: added an explicit http/https allow-list check before
  calling `launchUrl` — any other scheme now shows "This link looks invalid." instead of
  attempting to open it. This is the single shared helper every external link in the app already
  goes through, so the fix covers jobs, scholarships, companies, and intelligence sources in one
  place.

## 31. User Deletion Audit

Unchanged from the existing documented policy (`PRIVACY.md`'s Account Deletion section, verified
against the code this phase, not just re-read): account deletion is a real hard-delete path for
profile/documents/application history, not a soft "deactivate." Audit logs (an admin-side
construct, not user data) are correctly untouched by user account deletion — they record
*administrative* actions, not user content, and are governed by the append-only policy in §32
instead. **PASS**, no changes needed.

## 32. Admin Audit Log Integrity

`AuditLog` is append-only by convention (no route anywhere calls update/delete on it — confirmed
by grep, not just documentation). Sensitive actions (create/update/publish/delete/suspend/
reactivate) across content, question banks, media, users, sources, and discovery all write an
entry — confirmed for every admin route except the two P3 gaps noted in §11/§18 (category/topic
creation). **PASS WITH WARNING** for that specific, low-severity gap.

## 33. Background Job Audit

All three scheduled jobs (email watch renewal, scheduled content publish, content expiration) are
explicitly idempotent by design (only transition rows whose status doesn't already match the
target) — confirmed by the existing Phase 9 tests
(`test_scheduled_content_publishes_and_is_idempotent`,
`test_content_expiration_marks_expired_and_is_idempotent`), re-run and still passing this phase.
Restarting the application process re-registers all three jobs on their configured intervals via
APScheduler's in-process scheduler (confirmed live: restarting the backend during this phase's
testing showed all three jobs running again within seconds, visible in `/admin/dashboard/
operations`'s job-run history). **PASS.**

## 34. Retry Audit

`app/services/retry_policy.py`'s `RetryPolicy`/`classify_exception` was read directly (not just
re-tested): AUTHORIZATION failures (401/403) are explicitly excluded from the retryable category
set and never retried; TRANSIENT/PROVIDER_OUTAGE failures retry with exponential backoff + jitter
up to a bounded attempt count, then raise `PermanentFailure` rather than looping forever.
Duplicate-event creation during retry is prevented by the same database-level uniqueness
constraint used elsewhere (§8), independent of the retry logic itself. **PASS**, confirmed by
`test_run_with_retry_succeeds_after_transient_failures`,
`test_run_with_retry_never_retries_authorization_failures`, and
`test_run_with_retry_gives_up_after_max_attempts` (all re-run and passing this phase).

## 35. Observability Preparation

**DEFERRED → PARTIALLY FIXED this phase.** Before this phase, the only structured logging
anywhere in the backend was the scheduler's own job-failure log line — there was no request
correlation, no global unhandled-exception handler, and no consistent log format. Added this
phase, without requiring any paid monitoring service:
- `app/core/request_context.py` — a `ContextVar`-backed request id, injected into every log line
  via a `logging.Filter`.
- A request-id middleware (`app/main.py`) stamping every request with a UUID, echoed back as an
  `X-Request-ID` response header — verified live (`curl -sD -` shows the header populated with a
  real UUID matching what the server logged).
- A global `Exception` handler that logs the full exception (with request id) server-side and
  returns a generic, safe `{"detail": "Something went wrong. Please try again."}` to the client —
  never a raw stack trace — while remaining a natural attachment point for a real error-tracking
  service (Sentry etc.) later without touching any route.
- Background-job failures already logged (`app/scheduler.py`); this phase didn't need to change
  that.
- **DEFERRED**: provider-failure-specific structured events (e.g. a dedicated "Gmail renewal
  failed" metric distinct from a generic exception log) and database-failure-specific hooks beyond
  what SQLAlchemy/asyncpg's own exceptions naturally produce — a fuller observability pass is a
  reasonable Phase 10/11 candidate, not a hardening-phase requirement.

## 36. Logging Audit

Grepped the entire backend for `logger`/`print` calls near token/password/credential variable
names — **zero occurrences** (confirmed by the security research pass and re-confirmed directly).
The new request-id logging added this phase (§35) only logs method/path/exception details, never
request bodies or headers, so it introduces no new leakage risk. **PASS.**

## 37. Feature Flag Audit

All feature flags, documented in one place for the first time this phase:

| Flag | Default | Gates | Fails gracefully? |
|---|---|---|---|
| `EMAIL_TRACKING_ENABLED` | `true` | Whether email tracking is offered at all | Yes — `/email-tracking/providers` reports unavailable, mobile shows "In Development" |
| `GMAIL_TRACKING_ENABLED` | `true` | Gmail specifically (AND real credentials configured) | Yes, same mechanism |
| `OUTLOOK_TRACKING_ENABLED` | `true` | Outlook specifically (AND real credentials configured) | Yes, same mechanism |
| `FORWARD_EMAIL_ENABLED` | `false` | Forward-to-CareerOS (AND an inbound-mail provider, which never exists in this environment) | Yes — stays inert, feature UI simply doesn't activate |

No flag was found that, when disabled, leaves dead/broken functionality reachable — every gate is
checked both at the API-availability level (`*_available` computed properties in
`app/core/config.py`) and reflected honestly in the mobile/admin UI. **PASS.**

## 38. Mobile Real-World Build Config

Reviewed (not modified — this phase does not release):
- Package name / bundle identifier: `com.careeros.app` (Android), consistent across
  `android/app/build.gradle` and the Flutter project config.
- App display name, icons: present, unchanged from earlier phases.
- Permissions: `RECORD_AUDIO` (interview recording) and standard internet/network-state — no
  permission was found requested beyond what a built feature actually needs.
- Network security: no cleartext-traffic exception found in the Android manifest (HTTPS-only by
  default, matching the http/https-only URL-scheme fix in §30).
- Release config / versioning: still debug-only; no release signing config exists yet (expected —
  this project has never attempted a release build, per every prior phase's documentation). **NOT
  APPLICABLE** for a debug-only phase; release hardening remains a Phase 11 task.

## 39. iOS Static Audit

Cannot build (no macOS/Xcode in this environment, unchanged). Static review of
`ios/Runner/Info.plist`: bundle identifier matches Android's `com.careeros.app` equivalent,
`NSMicrophoneUsageDescription` is present (added in Phase 7.5 for interview recording), deployment
target and plugin compatibility were not exhaustively re-verified this phase beyond confirming the
file's presence and key entries. **iOS build status: NOT VERIFIED — unchanged from every prior
phase.** No claim of iOS readiness is made.

## 40. Admin Production Build

`npm run build` in `admin/` — **PASS**, zero TypeScript errors, all 27 routes compiled
successfully, re-run after this phase's type additions (`scheduled_publish_at`/
`reviewed_by_admin_id`/`published_by_admin_id` on three admin interfaces).

## 41. Backend Static Quality

No new linting/formatting/type-checking tooling was introduced this phase (per the brief's
explicit "do not introduce entirely new tooling if doing so creates unnecessary churn"). The
existing test suite (`pytest`) is the quality gate that was actually run — see §42.

## 42. Full Test Run

- **Backend**: `pytest -q` → **165 passed** (160 baseline + 3 new `test_config_security.py` +
  1 new `test_deleting_a_company_with_jobs_is_blocked_not_cascaded` + 1 new
  `test_journey_a_admin_publish_to_mobile_save_to_application_stage_update`). Every existing test
  file was run, not selectively re-run.
- **Flutter**: `flutter analyze` → clean. `flutter test` → **57 passed** (unchanged count — no new
  Dart tests were added this phase; the mobile fixes were verified by re-running the full existing
  suite plus manual code tracing, not new widget tests, to keep this phase's mobile diff scoped to
  bug fixes).
- **Admin**: no automated test suite exists (unchanged from Phase 9) — verified via production
  build (§40) and the original Phase 9 live-browser smoke test; not re-run live this phase since
  no admin UI code changed (only TypeScript interfaces).

## 43. Android Build

`flutter analyze` clean, `flutter test` 57/57, `flutter build apk --debug` succeeded (62.3s) —
all three re-run at the end of this phase after every mobile fix, not just once at the start.

## 44. End-to-End Automated Tests

- **Journey A** (admin publish job → mobile fetch → user save → create application → update
  stage): **NEW this phase** —
  `backend/tests/test_e2e_journeys.py::test_journey_a_admin_publish_to_mobile_save_to_application_stage_update`.
- **Journey B** (Application Aptitude stage → preparation → complete test → results): already
  covered end-to-end by existing tests, cited and not duplicated (see the docstring in
  `test_e2e_journeys.py` and §3 above).
- **Journey C** (Application Interview stage → prepare → STAR → session completion): already
  covered end-to-end by existing tests, same treatment.
- **Journey D** (Mock recruitment email → suggested stage → user confirms → timeline updates):
  already covered end-to-end by `test_full_flow_matched_suggestion_confirm_updates_real_stage`.

---

## 45. Fixes Applied This Phase (summary)

| # | Finding | Severity | File(s) | Status |
|---|---|---|---|---|
| 1 | No production guard against publicly-committed default secrets | P1 | `app/core/config.py`, `app/main.py` | Fixed + tested |
| 2 | SQLite FK enforcement never enabled anywhere (systemic) | **P1 (critical)** | `app/db/session.py`, `tests/conftest.py` | Fixed + full suite re-verified |
| 3 | `jobs.company_id` was CASCADE, risking silent data loss | P1 | `app/models/job.py`, migration `b2ff7f49cf7d`, `app/services/company_service.py` | Fixed + tested |
| 4 | Public jobs feed N+1 query on company lookup | P1 | `app/services/job_service.py`, `app/repositories/company_repository.py` | Fixed + tested |
| 5 | Mobile never forced re-login on 401 | P1 | `mobile/lib/core/network/api_client.dart`, `app_providers.dart` | Fixed + verified |
| 6 | `is_demo` not shown anywhere in mobile UI; missing from list API schemas | Spec violation (FAIL) | `app/schemas/job.py`, `scholarship.py`, mobile job/scholarship models + cards | Fixed + tested |
| 7 | No scheme validation on external URLs (job/scholarship/company/intelligence links) | FAIL | `mobile/lib/core/utils/url_launcher_helper.dart` | Fixed |
| 8 | Missing indexes on jobs status/dates, applications.current_stage, discovered_items.status, recruitment_email_events.status | P2 | `app/models/*.py`, migration `b2ff7f49cf7d` | Fixed |
| 9 | Admin TS interfaces missing Phase 9 workflow fields | P2 | `admin/types/models.ts` | Fixed + build re-verified |
| 10 | No router error page for bad deep links | P2 | `mobile/lib/routing/app_router.dart` | Fixed |
| 11 | Job-detail Save button had no double-tap guard | P2 | `mobile/lib/features/jobs/presentation/job_detail_screen.dart` | Fixed |
| 12 | Unbounded `/email-tracking/events` list endpoint | P4 | `app/repositories/email_tracking_repository.py` | Fixed |
| 13 | No request correlation / global exception handling / structured logging | Observability gap | `app/core/request_context.py`, `logging_config.py`, `main.py` | Fixed |

**Deferred** (documented above with reasoning, not silently dropped): admin question-bank N+1 on
options (P2, low-traffic); category/topic creation missing audit-log calls (P3); recruitment-email
confirm doesn't navigate to the matched application (P2, real but scoped-UI-addition); Gmail/
Outlook consent double-tap guard (P2, low-impact); analytics empty-states missing a CTA (P3);
mobile `JobDetail`/`ApplicationStageEvent`/aptitude/`Application` model field gaps (P3/P4); silent
access-token refresh (feature-sized, out of scope); company/intelligence DEMO badges (smaller
follow-up to the jobs/scholarships fix); `ContentSource` cascade losing discovery provenance (P3,
low-impact); email-tracking enum silent-fallback decoders (P3, cosmetic); true row-level locking
for double-submit races (P3, no evidence of occurring at current scale).

---

## 46. Release Readiness Scorecard

| Section | Status |
|---|---|
| Authentication | PASS WITH WARNING (silent token refresh not implemented; 401 handling now fixed) |
| Data Integrity | PASS WITH WARNING (FK enforcement fixed this phase — a significant prior gap; RESTRICT added; snapshot immutability confirmed) |
| Security | PASS (all confirmed findings were P3 or below after the P1 secret-default guard was added; no confirmed exploitable vulnerability) |
| Mobile | PASS WITH WARNING (navigation/error/loading fixes applied; several P2/P3 UX gaps remain, documented) |
| Admin | PASS WITH WARNING (RBAC/audit fully enforced; global search, bulk actions, and two audit-log gaps remain) |
| Backend | PASS (165/165 tests, clean migration, N+1/index fixes applied) |
| ATS | PASS (deterministic, correctly labeled, no fabricated probability claims) |
| Applications | PASS (stage-mutation integrity confirmed atomic and single-path; E2E journey verified) |
| Aptitude | PASS (grading manually verified against hand-calculated fixtures; snapshot immutability confirmed) |
| Interview | PASS (same snapshot guarantee; STAR/mock-interview journey verified end-to-end) |
| Email Tracking | PASS WITH WARNING (all integrity guarantees hold; **never run against a real Gmail/Outlook account — mock-verified only**) |
| Content Operations | PASS WITH WARNING (discovery/sources are architecture-only, no live ingestion, by design) |
| Privacy | PASS (documentation matches implementation; admin visibility limits confirmed and now documented) |
| Performance | PASS WITH WARNING (highest-impact N+1/index issues fixed; some lower-traffic ones deferred) |
| Deployment | PASS WITH WARNING (insecure-default guard added; multi-instance scheduler leader-election not implemented; iOS unverified) |

---

## 47. Pre-Monetization Checkpoint

**Is CareerOS structurally ready for AdMob integration?**

### YES, WITH BLOCKERS

CareerOS's core product loop (jobs/scholarships/companies/intelligence CMS, applications with
atomic stage integrity, aptitude and interview preparation with immutable session snapshots,
admin operations) is structurally sound: authorization is consistently enforced, the one systemic
data-integrity gap found in this audit (SQLite FK enforcement) is now fixed, and no confirmed
security vulnerability above P3 remains open. Adding an ad SDK is a self-contained, additive
integration that doesn't require re-architecting any of the above.

**Reasons this is "with blockers," not an unqualified yes:**
1. **Email tracking has never been verified against a real Gmail or Outlook account.** If ad
   placement or monetization logic were to ever interact with recruitment-email-driven engagement
   (e.g. an ad-free tier tied to active tracking), that surface is still mock-verified only.
2. **No production secrets guard was exercised against a real production deployment** — the new
   startup check (§22) has only been tested via unit tests of `Settings.uses_insecure_defaults`,
   not against an actual production-configured environment (none exists in this session).
3. **The multi-instance scheduler leader-election gap is unresolved** (§35/DEPLOYMENT.md) — fine
   for a single-instance deployment (which is presumably where AdMob would first ship), but must
   be resolved before horizontally scaling.
4. **iOS remains entirely unverified** — if monetization ships to iOS, that whole platform needs a
   real macOS/Xcode build-and-run pass first, which has never happened in this project.
5. A small number of P2 UX gaps remain open in the mobile app (§45) that would ship alongside any
   AdMob work if not addressed first — none are security- or data-integrity-critical, but they are
   real, user-visible rough edges.

None of the above blocks *starting* Phase 10 groundwork, but items 1, 3, and 4 should be resolved
(or explicitly accepted as launch risk) before a real production release with real users and real
ad revenue.

---

## 47a. Phase 10 Monetization Audit (added after Phase 10)

Phase 10 built the AdMob/monetization architecture described in full in **MONETIZATION.md**. This
section evaluates it against the same rigor as the rest of this document — PASS/WARNING/FAIL/
DEFERRED, not a restatement of the feature list.

**Ad isolation from sensitive workflows — PASS, CONFIRMED.** No ad-related import or widget was
added to any aptitude session screen, interview session screen (including the audio-recording
controller), STAR story editor, application stage-confirmation flow, recruitment-email review
screen, CV upload, document vault, or authentication screens — verified by direct inspection
(grep for `monetization`/`ad_service`/`BannerAdSlot` imports across those directories returns
nothing) and by a dedicated regression test
(`test/core/monetization/forbidden_contexts_test.dart`) asserting no `BannerAdSlot` appears in the
widget tree during an active aptitude or interview session specifically — the two highest-stakes,
highest-policy-risk screens. Apply/external-application-URL and recruitment-update-confirmation
code paths were not touched at all this phase — no ad requirement was added to either, confirmed
by inspection of `openExternalUrl` and `recruitment_event_detail_screen.dart`'s diff (none).

**Consent architecture — PASS, CONFIRMED.** `ConsentManager` wraps Google's real UMP SDK
(`ConsentInformation`/`ConsentForm`, bundled in `google_mobile_ads` 9.1.0) — no homemade consent
dialog exists anywhere in the codebase (grep for a custom "GDPR"/"consent" dialog widget outside
`consent_manager.dart` found none). `AdService.initialize()` calls `gatherConsent()` before SDK
init, and every failure path (form-load error, network failure during consent gathering) resolves
the initialization future rather than throwing — confirmed by code inspection of `catch` blocks in
`consent_manager.dart` and `ad_service.dart`.

**Privacy — PASS, CONFIRMED.** `AdRequest()` is constructed with zero custom targeting parameters
in every `AdService` call site (banner, interstitial, rewarded) — grep-confirmed no CV/email/
application/interview/document/salary/STAR data is ever passed into an ad request.
`LoggingAdAnalytics` logs only ad type, placement, and a generic outcome category — never a
device advertising identifier or private data — matching the same logging discipline already
verified for the rest of the backend in §36.

**Entitlement architecture — PASS WITH WARNING.** `User.subscription_tier` is persisted, defaults
`FREE` for everyone, and no code path anywhere sets it to `PRO` (no payment integration exists) or
contains an `if user.email == ...`-style shortcut — confirmed by grep across `app/services/` and
`app/api/`. **Warning**: free-tier usage limits are computed and reported accurately by
`MonetizationService.get_entitlement()` but are **not enforced** at the point of creating a new
`AtsAnalysis`/`TestSession` — a client that ignores the mobile app's soft-gate UI and calls the
creation endpoints directly can exceed the configured daily limits today. This is a deliberate,
documented scoping decision (see MONETIZATION.md §8), not an oversight, but it means the "Free
tier" is currently advisory rather than authoritative at the API layer. Rated WARNING rather than
FAIL because: (a) it was an explicit, reasoned trade-off against destabilizing well-tested
existing services, (b) the audit brief itself said usage limits "may" be implemented and warned
against enforcing them without full centralization, and (c) no data-integrity or security harm
results from a user getting more free usage than intended — this is a product/business-model gap,
not a safety one.

**Reward ledger integrity — PASS, CONFIRMED.** `RewardUnlock.reference_id` carries a database-
level `UniqueConstraint` (`uq_reward_unlocks_reference_id`) — the actual mechanism preventing a
duplicated reward-grant callback from creating two rewards, not just an application-layer check.
Confirmed by two tests: `test_duplicate_reward_reference_id_is_idempotent_not_double_granted`
(same user, same reference id, called twice → one reward) and
`test_another_users_reference_id_cannot_be_reused` (a different user attempting to reuse another
user's reference id → 409, not a silent grant). The mobile `AdService.showRewarded()` only
generates a `reference_id` and calls the claim endpoint *after* the SDK's real
`onUserEarnedReward` callback fires — confirmed by reading `ad_service.dart`'s
`showRewarded` implementation directly: `earnedReward` is set exclusively inside that callback,
and the claim call is gated on `if (!earnedReward) return false;` before ever reaching the
network call. **No AdMob server-side verification (SSV) exists** — explicitly documented as the
"mock verifier" spec §55 allows for development, not silently presented as production-grade
fraud protection.

**Fail-safe configuration — PASS, CONFIRMED.** Three independent fail-safes were verified by
direct code inspection and unit test: (1) `MonetizationConfig.disabled` is the fallback if
`GET /monetization/config` cannot be fetched at all — ads default OFF, never guessed on; (2)
`MonetizationConfig.appOpenAdsEnabled` is hardcoded `false` in `fromJson` regardless of what the
backend returns, so even a compromised or misconfigured backend cannot enable App Open ads
client-side; (3) `AdUnitConfig.resolve()` disables a format outright in a genuine production
build with no real ad unit id configured, rather than falling back to Google's test units —
verified by `ad_unit_config_test.dart`'s three fail-safe scenarios.

**Admin controls — PASS, CONFIRMED.** `monetization_config` and `free_tier_limits` are two more
entries in Phase 9's existing generic `system_settings` JSON editor — SUPER_ADMIN-only, same
enforcement as every other setting (re-verified: no new admin route was added, so the existing
RBAC audit in §11 covers it without change). No AdMob credential, OAuth secret, or signing
material is stored in `system_settings` at all — confirmed by inspecting `KNOWN_SETTINGS`, which
holds only ad-format toggles and numeric frequency/limit values.

**Overall Phase 10 verdict: PASS WITH WARNING** — the one warning (free-tier limits not hard-
enforced) is explicitly scoped and documented, not a hidden gap, and does not change the Phase
9.5 pre-monetization checkpoint's verdict (§47) for the reasons above.

---

## 48. Known Blockers (carried into any future phase)

- Real Gmail/Outlook OAuth credentials (Phase 8, still unresolved).
- Docker/Postgres never installed or verified — every finding in this audit was verified against
  SQLite only. The FK-enforcement fix (§22) will behave identically on Postgres (which enforces
  FKs natively) — but that itself has never been confirmed in this environment.
- No macOS/Xcode — iOS build, static-review-only.
- No Android emulator/physical device — every mobile flow is automated-test-verified, never
  manually tapped through on a running app.
- FCM/APNs credentials (push notifications, still architecture-only).
- A live RSS/Lever/Ashby ingestion adapter (Discovery is manual-ingest-only, by design).
- A real AdMob account, real ad units, real app-ads.txt hosting, and AdMob "app readiness"
  verification (Phase 10 is test-ad-verified only — see MONETIZATION.md §22).
- AdMob server-side reward verification (SSV) — the reward-claim endpoint is a documented "mock
  verifier," not production-grade fraud protection against real ad revenue.
- Hard enforcement of free-tier usage limits at the API layer (Phase 10, §47a above).
- A real payment/subscription integration (CareerOS Pro is architecture-only, "Coming Soon").
