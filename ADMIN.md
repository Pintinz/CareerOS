# CareerOS — Admin CMS & Content Operations

Covers the Next.js admin application (`admin/`) and its backend (`backend/app/api/v1/admin/*`),
built in Phase 9. This is the operational control center for CareerOS content and monitoring — see
`PROJECT_STATUS.md`'s Phase 9 section for what shipped vs. what was explicitly deferred, and
`ARCHITECTURE.md` for the scheduler/retry-policy/data-model detail.

## Roles (RBAC)

Four roles exist on `AdminUser.role`: `SUPER_ADMIN`, `ADMIN`, `EDITOR`, `REVIEWER`. **Backend
authorization is authoritative everywhere** — every admin route depends on a role-checking FastAPI
dependency; the frontend's role-based nav hiding (`admin/lib/useAdminRole.ts`) is a UI convenience
only and must never be treated as a security boundary.

- **SUPER_ADMIN** — everything, plus System Settings and (together with ADMIN) suspending/
  reactivating users and reading the Audit Log.
- **ADMIN** — everything except System Settings.
- **EDITOR** — content CRUD (jobs/scholarships/intelligence/companies/question banks/media/sources/
  discovery/notifications), no user suspension, no settings, no audit log.
- **REVIEWER** — read/review-oriented actions (discovery queue review, content review-status
  transitions); the exact create/delete boundary for REVIEWER follows the same dependency used for
  EDITOR-level routes in `app/api/v1/admin/*` — check the specific route's `Depends(...)` for the
  authoritative answer rather than assuming from this doc.

The first `SUPER_ADMIN` is created by `ensure_seed_admin()` on backend startup from
`ADMIN_SEED_EMAIL`/`ADMIN_SEED_PASSWORD` (no-op if unset or if any admin already exists — see
DEPLOYMENT.md). There is no public self-registration endpoint for admin accounts by design.

## The 15 navigation areas

| Area | Route | Backend |
|---|---|---|
| Dashboard | `/` | `GET /admin/dashboard` |
| Jobs | `/jobs` | `/admin/jobs` (pre-existing, extended with workflow tracking + audit logging) |
| Scholarships | `/scholarships` | `/admin/scholarships` (same) |
| Companies | `/companies`, `/companies/[id]` | `/admin/companies` (extended with structured intelligence fields) |
| Company Intelligence | `/intelligence` | `/admin/intelligence` (new CMS UI this phase; API pre-existing) |
| Aptitude Question Bank | `/questions/aptitude` | `/admin/aptitude/questions` (+ bulk-import) |
| Interview Question Bank | `/questions/interview` | `/admin/interview/questions` (+ bulk-import) |
| Media Library | `/media` | `/admin/uploads` |
| Content Sources | `/sources` | `/admin/sources` |
| Discovery Queue | `/discovery` | `/admin/discovery` |
| Users | `/users` | `/admin/users` |
| Notifications | `/notifications` | `/admin/notifications` |
| Operations | `/operations` | `/admin/dashboard/operations` |
| Audit Logs | `/audit` (SUPER_ADMIN/ADMIN) | `/admin/audit` |
| System Settings | `/settings` (SUPER_ADMIN only) | `/admin/settings` |

## Editorial workflow (content lifecycle)

Jobs, Scholarships, and Intelligence Posts share one status lifecycle:
`DRAFT → REVIEW → PUBLISHED → ARCHIVED`, with `EXPIRED` and `REJECTED` as additional terminal-ish
states. `reviewed_by_admin_id`/`published_by_admin_id` are set exactly once, on first transition
into `REVIEW`/`PUBLISHED` respectively — editing a published item afterward never overwrites who
originally reviewed or published it.

**Scheduled publishing and expiration are real, not aspirational**: setting `scheduled_publish_at`
on a DRAFT item means the background scheduler (`app/scheduler.py`, runs every 15 minutes) will
transition it to PUBLISHED on its own — the admin does not need to keep a browser tab open.
Content expiration runs hourly: Jobs/Scholarships past their deadline move to `EXPIRED`
automatically (Scholarships use `application_deadline`; Jobs use their own expiry field).
Intelligence Posts are deliberately excluded from automatic expiration — news doesn't go stale the
way a time-bound listing does.

## Question bank management

Both Aptitude and Interview question banks support full CRUD plus **CSV bulk import**
(`POST .../bulk-import`, multipart file upload). Every row is validated independently — a malformed
row never silently corrupts the import or gets skipped without explanation. The response always
reports three things separately: `imported` (count), `skipped` (duplicates — see below), and
`errors` (a list of `{row, reason}` for genuinely invalid rows). Duplicate detection compares
normalized question text (lowercased, punctuation-stripped) against both the existing bank and
earlier rows already processed in the same file — a duplicate is reported in `duplicate_warnings`
and skipped, never imported twice and never a hard error.

Aptitude questions support `IMAGE_BASED` type authoring (upload the question image plus per-option
images) via the existing shared image-upload pipeline (Phase 7.5) with alt-text fields. Correct
answers and other grading-relevant fields are never exposed in the public consumer API — only in the
authenticated admin endpoints.

## Media library

`GET /admin/uploads` lists every uploaded asset with its filename/mime/dimensions/size/uploader.
`DELETE /admin/uploads/{id}` refuses (409) to delete an asset if its URL is still referenced by any
known content column — jobs/companies/scholarships/intelligence posts' thumbnail/logo/banner/image
fields, or a question/option's image field. This is implemented as a fixed-list raw-SQL text search
(`_URL_COLUMNS` in `app/api/v1/admin/uploads.py`), not a real reference-counting join table — safe
because the column list is a hardcoded constant, never user input, but an approximation worth
replacing with a real reference table if the media library grows large.

**Organization logos.** Company pages ("Fetch logo from website") and scholarship forms ("Fetch
provider logo") call `POST /admin/uploads/image/from-website`, which reads the official site's declared
icons (apple-touch-icon, large PNG icons, schema.org Organization `logo`, then `/apple-touch-icon.png`
and `/favicon.ico`) through the discovery HTTP client (robots.txt, SSRF checks, size limits), decodes
and re-encodes the image as a square PNG (max 256px) and stores it as a media asset — a copy, never
a hotlink. SVG-only sites and icons under 48px return a clear error; upload a logo instead. Nothing
changes until the form is saved. Admin sessions that expire (30-minute tokens) now return to sign-in.

## Content sources & discovery queue

The admin works like an editorial research desk: **Sources → Discovery → Verification → Draft →
Publish → Monitor.** Full engine design: **DISCOVERY_ENGINE.md**.

- **Sources** (`/sources`): register official careers pages, ATS boards, newsrooms, universities,
  scholarship providers and feeds, with content types, public adapter identifiers (board token etc. —
  secrets are rejected), polling and crawl interval. The health table shows active/paused, ownership
  verification, trust level, last check/success/failure (with backoff), items discovered/awaiting
  review/published and the last run. **Run discovery** enqueues a background run and returns at once;
  **Runs** shows history. Only ADMIN/SUPER_ADMIN may change trust level, ownership verification or
  allow auto-publishing; trust never grants publish permission.
- **Discovery queue** (`/discovery`): tabs All / Jobs / Scholarships / Internships / Graduate Programs
  / Fellowships / Intelligence; filters for source, company, country, trust, status, date and
  duplicates; each row shows type, title, organization, source, canonical URL, published date,
  deadline, trust, extraction confidence, verification state and whether it is new, a duplicate or an
  update of an existing record. **Run due sources** and **Verify active listings** start background
  work; a panel lists changes detected on already-published records (apply/dismiss; confirm or keep a
  detected removal).
- **Review** (`/discovery/{id}`): source evidence (source quality, matched organization or a company
  proposal, original title and URL, external id, requisition, dates, method, checks, flags, facts
  dropped for lack of evidence, instruction-like page text, dedup reasons, raw payload) side by side
  with the editable CareerOS record, or with the existing record and its detected changes. Actions:
  Create draft, Publish (blockers explained), Ignore, Reject, Create company.

Nothing is published by default. Discovery-only (aggregator) items can't be published until an
official URL is set, and a listing that already exists in CareerOS is reviewed as changes, not
published again. The manual `POST /admin/discovery/ingest` entry point remains for things an editor
spots by hand.

### Career sources (official company career feeds)

**Sources** is also the career-feed console: readiness (ready structured / ready official pages / needs
configuration / manual only / blocked) with the audit note, health, ATS provider and adapter, last sync,
HTTP status and listings in scope, country scope. Actions: **Run sync now** (queued, returns at once),
**Test connection** (reads at most five listings, stores nothing), **Edit** (automatic sync and interval,
auto-create drafts, country scope, listing pages, job-search URL, ATS, readiness), Enable/Disable, Runs,
Items. Admins can **Import starter pack** (dry-run preview first; existing sources keep their polling,
trust and publishing settings). The Discovery queue shows external job ids, source types, first-discovered
dates, missed syncs and a "View original" link, with Create draft on each row; its dashboard adds healthy
and failed sources, last sync, new/updated items, possibly removed listings and live jobs by country and
industry. See CAREER_SOURCE_INTEGRATION.md and docs/career_sources.md.

## Notifications

Creating and "sending" a notification campaign is real data-model work, but there is **no FCM/APNs
integration** in this environment. `POST /admin/notifications/{id}/send` marks the campaign `SENT`
and honestly records `recipient_count: 0` — it does not fabricate a delivery count, and no device
anywhere actually receives anything. This is architecture-complete, delivery-incomplete by design
(see PROJECT_STATUS.md's Phase 9 section and ARCHITECTURE.md's environment-gated-integrations
table for the pattern this follows elsewhere in the codebase).

## Audit logging

Every create/update/publish/archive/delete/suspend/reactivate action across content, question
banks, media, users, sources, and discovery writes one `AuditLog` row (admin id, action, entity
type/id, a JSON metadata blob, timestamp) via `app/services/audit_service.py`'s single `record()`
function. The table is append-only by convention — no route ever updates or deletes a row. Metadata
never contains secrets, tokens, or raw user content (see PRIVACY.md).

## System settings

SUPER_ADMIN-only (`GET/PUT /admin/settings`). The registry (`system_settings_service.KNOWN_SETTINGS`)
is seeded from the compiled-in defaults for ATS scoring weights, interview-readiness weights,
question-generation defaults, and email-classifier confidence thresholds. **Only the email-
classifier confidence thresholds are actually consumed at runtime** — `EmailTrackingService.
process_message` reads them via `system_settings_service.get_confidence_thresholds()` before every
classification. The ATS-weight and interview-readiness-weight settings are stored, editable, and
visible in the admin UI, but not yet wired into `app/matching/` or `app/interview/scoring.py` — a
documented partial-wiring decision, not an oversight (see PROJECT_STATUS.md's Next Tasks). Secret
API keys are never stored here — they remain in environment/secret management exclusively.

## Operational monitoring

`GET /admin/dashboard/operations` (rendered by `admin/app/operations/page.tsx`) surfaces three
things honestly:
- **Email tracking**: active Gmail/Outlook connection counts, reauthorization-required count, sync
  errors, and provider health — which reads `DISABLED` or `MOCK`, **never `"Verified"`**, since no
  real Gmail or Outlook account has ever exercised this code in this environment (see
  PROJECT_STATUS.md — do not describe either provider as production-verified).
- **Content ingestion**: active/failed source counts, items discovered today, items awaiting review.
- **Background jobs**: the scheduler's own run history for email watch renewal, scheduled
  publishing, and content expiration — last run time, success/failure, duration, and error message
  per job (in-memory, process-local; resets on backend restart, since it describes "since this
  process started," not a durable record — that's what the Audit Log is for).

## Phase 9.5 audit hardening

A full-system audit (see **SYSTEM_AUDIT.md**) exercised the admin surface described above and made
two changes relevant here: `admin/types/models.ts`'s `JobAdmin`/`ScholarshipAdmin`/
`IntelligencePostAdmin` TypeScript interfaces were missing the `scheduled_publish_at`/
`reviewed_by_admin_id`/`published_by_admin_id` fields the backend actually returns (fixed —
production build re-verified clean); and deleting a Company that still has Jobs now returns a
clean 409 ("This company still has jobs...") instead of either silently cascading the delete or
raising a raw database error — see DATABASE.md for why (`jobs.company_id` changed from `CASCADE`
to `RESTRICT`, and SQLite foreign-key enforcement itself had never been turned on before this
phase). No admin UI behavior changed as a result — only correctness of an edge case and type
completeness.

## What is explicitly not built (see PROJECT_STATUS.md for the full list)

Live RSS/Lever/Ashby ingestion, real push notification delivery, apply-click tracking and per-content
analytics, global cross-entity admin search, bulk content actions, job/scholarship mobile-preview
before publish, a rich-text/sanitized editor (plain `<textarea>` throughout), edit-concurrency/
version-conflict detection, a formal accessibility audit, and automated admin UI tests (this phase's
admin UI was verified by hand in a live browser against the running backend instead — see
PROJECT_STATUS.md's Tests section for exactly what was clicked through and the one real bug that
live testing caught and a clean TypeScript build could not).
