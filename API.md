# CareerOS — API

Base URL (local dev): `http://localhost:8000/api/v1`

## Conventions

- JSON in, JSON out. Errors follow `{"detail": "...", "code": "..."}`.
- Auth: `Authorization: Bearer <jwt>`. Consumer JWTs (`users`) and admin JWTs (`admin_users`) are
  issued from separate endpoints and are not interchangeable — an admin router rejects a consumer
  token and vice versa.
- Pagination: `?page=1&page_size=20`, response envelope `{"items": [...], "page": 1, "page_size": 20,
  "total": 123}`.
- All list endpoints support `?search=` where full-text search is meaningful (jobs, scholarships,
  companies, news) via Postgres full-text search — no Elasticsearch dependency.

## Implemented endpoints (Phases 0-1)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | none | Liveness check — returns `{"status": "ok", "version": "..."}` |
| POST | `/api/v1/auth/register` | none | `{email, password}` → `TokenResponse`. Creates an empty `profiles` row. 409 on duplicate email. |
| POST | `/api/v1/auth/login` | none | `{email, password}` → `TokenResponse`. 401 on bad credentials. |
| POST | `/api/v1/auth/refresh` | none | `{refresh_token}` → new `TokenResponse`. 401 if invalid/expired/wrong token type. |
| GET | `/api/v1/auth/me` | bearer | → `UserOut` (`id`, `email`, `is_verified`). |
| DELETE | `/api/v1/auth/me` | bearer | Hard-deletes the user (cascades to `profiles`). 204. |
| GET | `/api/v1/profile` | bearer | → `ProfileOut`. 404 if somehow missing. |
| PUT | `/api/v1/profile` | bearer | Partial update (`ProfileUpdate`, all fields optional) → `ProfileOut`. `null`/omitted fields are left unchanged, not cleared. |

Not yet implemented: logout (client just discards tokens locally for now — no server-side revocation/
blocklist exists), forgot-password, email verification, Google/Apple Sign-In.

## Implemented endpoints (Phase 2 — Opportunities)

Consumer routes accept an optional `Authorization: Bearer <user token>` — when present, list/detail
responses include an accurate `is_saved`; when absent they still work (anonymous browsing).

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/companies` | optional | Paginated, `?search=`. Active companies only. Each item includes `is_following` (false when anonymous). |
| GET | `/api/v1/companies/{id_or_slug}` | optional | 404 if not found or inactive. |
| POST/DELETE | `/api/v1/companies/{id}/follow` | required | Follow/unfollow a company. |
| GET | `/api/v1/jobs` | optional | Paginated. Filters: `search, country, location, industry, employment_type, work_mode, experience_level, is_featured, company_id`. `sort=newest\|recommended\|deadline` (`recommended` is currently featured-first-then-newest — a documented placeholder, not the real matching engine). Published + active + unexpired jobs only. |
| GET | `/api/v1/jobs/{id_or_slug}` | optional | 404 unless `status=PUBLISHED`, `is_active`, and not past `expires_at`. |
| POST/DELETE | `/api/v1/jobs/{id}/save` | required | Save/unsave for the current user. |
| GET | `/api/v1/scholarships` | optional | Paginated. Filters: `search, country, degree_level, funding_type`. |
| GET | `/api/v1/scholarships/{id_or_slug}` | optional | Same visibility rule as jobs (minus the expiry check — scholarships don't have `expires_at`). |
| POST/DELETE | `/api/v1/scholarships/{id}/save` | required | Save/unsave for the current user. |
| GET | `/api/v1/intelligence` | optional | Paginated. Filters: `search, category, company_id, followed_only` (requires auth; returns empty for anonymous callers rather than erroring). |
| GET | `/api/v1/intelligence/{id_or_slug}` | none | 404 unless published + active. |
| GET | `/api/v1/me/saved-jobs` | required | Paginated list of the user's saved jobs. |
| GET | `/api/v1/me/saved-scholarships` | required | Paginated list of the user's saved scholarships. |
| GET | `/api/v1/me/followed-companies` | required | All companies the user follows (not paginated — expected to stay small). |
| POST | `/api/v1/admin/auth/login` | none | Admin login → `TokenResponse` (audience-scoped, see below). |
| GET | `/api/v1/admin/auth/me` | admin bearer | Current admin's id/email/role. |
| GET/POST | `/api/v1/admin/companies` | admin bearer | List (any role incl. REVIEWER) / create (EDITOR+). |
| GET/PUT | `/api/v1/admin/companies/{id}` | admin bearer | Same role split as above. |
| DELETE | `/api/v1/admin/companies/{id}` | admin bearer | ADMIN/SUPER_ADMIN only. |
| GET/POST | `/api/v1/admin/jobs` | admin bearer | List/create. `?status=` filters by `ContentStatus`. |
| GET/PUT | `/api/v1/admin/jobs/{id}` | admin bearer | Get/update (including publish via `{"status":"PUBLISHED"}`). |
| POST | `/api/v1/admin/jobs/{id}/duplicate` | admin bearer (EDITOR+) | Clones a job as a new `DRAFT` titled `"<title> (Copy)"`. |
| DELETE | `/api/v1/admin/jobs/{id}` | admin bearer (ADMIN+) | |
| GET/POST/PUT/DELETE | `/api/v1/admin/scholarships[/{id}]` | admin bearer | Same role split as jobs. |
| GET/POST/PUT/DELETE | `/api/v1/admin/intelligence[/{id}]` | admin bearer | Same role split as jobs. `company_id` is optional (industry-wide news isn't always company-specific). |
| POST | `/api/v1/admin/uploads/image` | admin bearer (EDITOR+) | Multipart `file`, optional form field `alt_text`. JPG/PNG/WEBP, 8MB max — **actually decoded with Pillow** (Phase 7.5), not just checked by extension/Content-Type; rejects content that doesn't decode as a real image (422) and dimensions over 4096px either side. Returns `{"url", "media_asset_id", "alt_text", "width", "height", "mime_type", "file_size"}` served from local disk under `/uploads/*` (spec Rule 3 — swap for a cloud `StorageProvider` later without changing callers). Every call also creates a `MediaAsset` audit row. This is the **one shared upload endpoint** used by every feature needing an uploaded image (jobs/companies/intelligence posts, and now aptitude/interview question images too) — never duplicated per-feature. |

**Admin vs. consumer tokens are not interchangeable.** An admin access token carries `aud: admin` and
a consumer token carries `aud: user`; each router's dependency rejects the wrong audience with 401 —
verified by `tests/test_admin_companies.py::test_admin_token_cannot_access_consumer_me` and
`test_consumer_token_cannot_access_admin_routes`.

**Content visibility rule** (jobs and scholarships alike): a record is visible on a public/consumer
route only when `status == PUBLISHED` and `is_active == True`, and (jobs only) `expires_at` is either
unset or still in the future. Every other combination (`DRAFT`, `REVIEW`, `ARCHIVED`, `is_active=False`,
or an expired job) 404s on the consumer route even though the admin route can still see and edit it.

## Implemented endpoints (Phase 3 — ATS)

All require a consumer bearer token (`Authorization: Bearer <user token>`).

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/ats/cv` | Multipart: `file` (PDF/DOCX/TXT, 5MB max), optional `name`, `is_primary`. Extracts and stores plain text server-side (`app/services/document_extraction.py`); rejects unsupported types/unreadable files with 422. |
| GET | `/api/v1/ats/cv` | Lists the current user's uploaded CVs. |
| DELETE | `/api/v1/ats/cv/{id}` | |
| POST | `/api/v1/ats/analyze` | Body: exactly one of `cv_document_id`/`cv_text`, and exactly one of `job_id`/`job_description` (+ optional `job_title` when pasting a description). Returns `AtsAnalysisOut` — `overall_score`, a `score_breakdown` naming all 8 weighted components (see ARCHITECTURE.md), `strong_matches`, `missing_keywords`, `formatting_issues`, `missing_metrics_note`. Runs the deterministic engine in `app/matching/ats_engine.py` — no external AI call. |
| GET | `/api/v1/ats/analyses` | Paginated analysis history for the current user. |

## Implemented endpoints (Phase 5 — Applications)

All require a consumer bearer token. Applications are strictly user-owned — every route 404s (not
403) on another user's application, so existence isn't leaked either.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/applications` | Body: either `job_id` (pre-fills company/role/location/job_url from the real job) or both `company_name` + `role_title` for a manual entry not in our `jobs` table (spec §36). Optional `current_stage` (default `SAVED`), dates, salary, contact info, `cover_letter_text`. Creates the first timeline event automatically. |
| GET | `/api/v1/applications` | Paginated, `?stage=` filter. |
| GET | `/api/v1/applications/{id}` | Full detail including `timeline` (all stage events, oldest first) and `notes` (newest first). |
| PUT | `/api/v1/applications/{id}` | Partial update of the non-stage fields (location, dates, salary, contact, cover letter, etc.) — does **not** change `current_stage`; use the `/stage` endpoint for that so a timeline event is always recorded. |
| POST | `/api/v1/applications/{id}/stage` | Body: `stage`, optional `note`, optional `occurred_at` (backdating). Updates `current_stage` and appends an `application_stage_events` row — this is the *only* way `current_stage` changes, by design (spec §42's "never silently change a stage" principle applies here too, even without email detection yet: a stage change always leaves an audit trail). |
| POST | `/api/v1/applications/{id}/notes` | Body: `text`. |
| DELETE | `/api/v1/applications/{id}` | |
| GET | `/api/v1/me/applications-summary` | `{"active_applications": <count>}` — excludes `HIRED`/`REJECTED`/`WITHDRAWN`/`EXPIRED`. Backs the Home dashboard's "Active Applications" card with a real number. |

## Implemented endpoints (Phase 6 — Aptitude Testing)

All consumer routes require a bearer token and are strictly per-user — a session that isn't yours
404s (never 403), matching the isolation pattern established for `/applications`. Grading is always
backend-authoritative; `is_correct` is never sent to the client before submission.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/aptitude/categories` | The six fixed sections (Numerical/Verbal/Abstract/Logical/Situational Judgement/Technical). |
| GET | `/api/v1/aptitude/topics` | Optional `?category_id=`. |
| POST | `/api/v1/aptitude/sessions` | Body (`TestSessionCreate`): `mode` (`PRACTICE`/`TIMED`/`MOCK`/`JOB_SPECIFIC`/`FIELD_SPECIFIC`), `sections` (category slugs; empty = all), `difficulty` (`EASY`/`MEDIUM`/`HARD`/`EXPERT`/`MIXED`, default `MIXED`), `question_count` (1-100), `timing` (`UNTIMED`/`OVERALL`), `time_limit_minutes` (required if `OVERALL`), optional `application_id`/`job_id` (resolves field/industry/job_role context for Technical-topic bias — see `technical_topic_map.py`), optional `topic_slugs` (explicit override, used by "Practice Weak Areas" — bypasses job/field inference entirely). Generates the question set deterministically (no AI), snapshots every question, and returns `TestSessionDetailOut` (includes `questions`, `server_time`, `remaining_seconds`). Creating a session starts it immediately (`status=IN_PROGRESS`). 422 if no active question matches the filters at all. |
| GET | `/api/v1/aptitude/sessions` | Paginated history, `?status=` filter. |
| GET | `/api/v1/aptitude/sessions/{id}` | Full detail. Lazily auto-submits and returns the post-expiry state if `expires_at` has passed — the client never needs to call submit itself on timeout, though it may. |
| PUT | `/api/v1/aptitude/sessions/{id}/answers/{question_id}` | `question_id` here is the **snapshot** id (`test_session_questions.id`), returned as each question's `id` in the session payload. Body: `selected_option_ids`/`answer_numeric_value`/`time_spent_seconds`. 409 if the session is no longer `IN_PROGRESS` (submitted, or just auto-submitted by this same call's expiry check). |
| POST | `/api/v1/aptitude/sessions/{id}/flag/{question_id}` | Toggles the flag on that question; returns the updated question. |
| POST | `/api/v1/aptitude/sessions/{id}/submit` | Grades all answers (marks-weighted overall score; per-question-type: choice questions by exact selected-set match, numeric by tolerance comparison), computes `section_breakdown` (accuracy per category), and returns `TestResultOut`. Idempotent — calling it again after submission just returns the existing result rather than erroring. |
| GET | `/api/v1/aptitude/sessions/{id}/results` | 409 until submitted. |
| GET | `/api/v1/aptitude/sessions/{id}/review` | 409 until submitted — only then does the response include which option was correct (`ReviewOptionOut.is_correct`) alongside the user's answer and the stored explanation. |
| GET | `/api/v1/aptitude/analytics` | `AptitudeAnalyticsOut` — tests completed, questions answered, average/best score, average time per question, `by_category`/`by_topic` breakdowns — computed from the user's own submitted sessions only. |
| GET | `/api/v1/aptitude/recommendations` | Weak topics (accuracy < 60%, and only once a topic has at least 3 attempted questions — avoids drawing conclusions from a tiny sample) with each topic's slug, ready to feed straight back into `POST /sessions` as `topic_slugs`. |

Admin question-bank CRUD (categories/topics/questions/options) exists under `/api/v1/admin/aptitude/*`
(role-gated the same way as jobs/scholarships — EDITOR+ write, REVIEWER read) even though the admin
web UI for it isn't built until Phase 9; it's never exposed to a normal consumer token.

## Implemented endpoints (Phase 7 — Interview Preparation & STAR)

All consumer routes require a bearer token and are strictly per-user (404, never 403, on a session/
story that isn't yours). Practicing here **never** mutates a linked application's real
`current_stage` or `assessment_completed` — see PRIVACY.md.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/interview/categories` | The ten fixed categories (spec §6). |
| GET | `/api/v1/interview/topics` | Optional `?category_id=`. |
| POST | `/api/v1/interview/sessions` | Body (`InterviewSessionCreate`): `mode` (`PRACTICE`/`MOCK`), `categories` (category slugs; empty = all), `category_counts` (optional category-slug → exact-count map, for a Mock Interview's "Technical 4 / Behavioral 3 / Safety 2 / HR 1" builder — overrides `categories`/`question_count`), `difficulty`, `question_count`, `time_per_question_seconds` (self-paced display only — never enforced server-side), optional `application_id`/`job_id`/`company_id` (resolves job/company context for Technical-topic and company-tagged-question bias), optional `experience_level` (excludes `EXPERT` questions from a `MIXED` session unless the difficulty is explicitly `EXPERT` — spec §7). Deterministic generation (no AI), immutable per-question snapshots. Creating a session starts it immediately. 422 if nothing matches. |
| GET | `/api/v1/interview/sessions` | Paginated history. |
| GET | `/api/v1/interview/sessions/{id}` | Full detail, including each question's `suggested_star_story_ids` (spec §16 — matched by the user's own STAR story categories against the question's `star_tags`, computed fresh on every read). |
| PUT | `/api/v1/interview/sessions/{id}/answers/{question_id}` | `question_id` is the snapshot id. Body: `answer_text`/`notes`/`audio_path`/`audio_duration_seconds`/`self_rating` (1-5)/`used_star`/`gave_measurable_result`/`answered_exact_question`/`is_skipped`/`is_marked_practiced`/`is_saved`. Returns the updated question, including a deterministic `structure_check` (word count, metric-presence, STAR-keyword hints — spec §22-23's "Answer Structure Check", explicitly never called AI analysis) when `answer_text` is present. 409 once the session is no longer `IN_PROGRESS`. |
| POST | `/api/v1/interview/sessions/{id}/complete` | Marks the session `COMPLETED` and returns `SessionCompletionOut` (questions completed/skipped, average self-rating, average answer length, STAR usage rate, per-category breakdown, areas practiced vs. still uncovered). Idempotent — safe to call again on an already-completed session, which just recomputes and returns the same stats. |
| GET | `/api/v1/interview/analytics` | Sessions completed, questions practiced, average self-rating, STAR stories created/ready, company-prep-completed count, technical topics covered, per-category completion — all **system-calculated** from the user's own session/answer/STAR history. |
| GET | `/api/v1/interview/readiness` | Optional `?application_id=` to scope Company/Job-Specific components to that application's linked job/company. Returns `overall` (weighted per spec §11's 25/25/15/15/15/5 split, renormalized across whichever components are applicable) plus the per-component breakdown, or `insufficient_data: true` with `overall: null` rather than inventing a number. |
| GET | `/api/v1/interview/prep/company` | Requires `?application_id=`. Real company overview (from `companies`), recent developments (from `intelligence_posts`, company-scoped), likely topics (job-role keyword mapping), other open roles at that company, and a fixed disclaimer that this is CareerOS practice, not an official employer interview guide (spec §9/§35). |
| GET / PUT | `/api/v1/interview/prep/progress`, `/prep/checklist`, `/prep/questions-to-ask`, `/prep/topics` | All accept optional `?application_id=` (omitted = the general, non-application-linked progress row). Checklist and questions-to-ask completion persist per spec §26-27; topic review persists which aptitude-taxonomy technical topics (by slug) the user has marked reviewed (spec §28). |
| GET / POST | `/api/v1/star-stories` | List (optional `?category=`) / create a STAR story. Every response includes a `completeness` object (per-section status: `missing`/`brief`/`complete`/`strong`, plus named `gaps` like `missing_measurable_outcome`) computed deterministically (`app/interview/star_check.py`) — never AI-graded. |
| GET / PUT / DELETE | `/api/v1/star-stories/{id}` | |

Admin question-bank CRUD exists under `/api/v1/admin/interview/*` (categories/topics/questions,
same EDITOR+/REVIEWER role split as aptitude/jobs), including assigning a question to a company,
role, industry, or experience level — the admin web UI for it is deferred to Phase 9.

## Implemented endpoints (Phase 7.5 — Media, Assessment & Interview Hardening)

All consumer routes require a bearer token and are strictly per-user (404, never 403). `StarStory`/
`PreparationProgress` updates below accept an optional `expected_version` for offline-conflict
detection — omit it to update unconditionally (the pre-Phase-7.5 behavior), or pass the last-seen
`version` to get a 409 instead of silently overwriting a newer remote edit.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/interview/sessions/mock-mix-preview` | Query: `question_count` (default 10), optional `application_id`/`job_id`. Returns `MockMixPreviewOut` (`category_counts`, `category_names`, `source`: `"role_default"` or `"general_default"`) — the role-specific default category mix (`app/interview/role_mix.py`) a Mock Interview's "Automatic Mix" would apply, without creating a session. Registered before `GET /sessions/{id}` so the literal path always wins the route match. |
| POST | `/api/v1/interview/sessions` | (Extends the Phase 7 endpoint.) New optional body field `auto_mix: bool` — when `true` and `category_counts` isn't given explicitly, derives it from the role-specific default distribution for the resolved field/industry/job_role, falling back to a general default mix when no role match is found. |
| POST | `/api/v1/interview/recordings` | Body: `session_id`, `session_question_id` (the session-scoped question id, same id used for `/answers/{id}`), `local_path`, `duration_seconds`, optional `title`. Creates a metadata-only row (`upload_status` always `"local_only"` — the audio file itself is never uploaded). 404 if the session or session-question isn't owned by the caller. |
| GET | `/api/v1/interview/recordings` | Lists the current user's recording metadata, newest first. |
| PUT | `/api/v1/interview/recordings/{id}` | Body: `title`. Rename. 404 if not owned. |
| DELETE | `/api/v1/interview/recordings/{id}` | Deletes the metadata row (204). Does **not** delete the local audio file on the device — that's the mobile client's responsibility, since the file lives on-device, not on this backend. |
| PUT | `/api/v1/star-stories/{id}` | (Extends the Phase 7 endpoint.) Now accepts `expected_version`; response now includes `version`. |
| PUT | `/api/v1/interview/prep/checklist`, `/prep/questions-to-ask`, `/prep/topics` | (Extend the Phase 7 endpoints.) Now accept `expected_version`; `PreparationProgressOut` now includes `version`. |

`Question`/`QuestionOption`/`SessionQuestionOut`/`ReviewQuestionOut`/`QuestionAdminOut`/`OptionOut`
(aptitude, Phase 6) all gained `question_image_alt_text`/`option_image_alt_text` fields — neutral
structural alt text, immutably snapshotted per session like every other question field (see
ARCHITECTURE.md and DATABASE.md).

## Implemented endpoints (Phase 8 — Smart Recruitment Email Tracking)

All `/email-tracking/*` routes require a consumer bearer token and are strictly per-user (404,
never 403, on a connection/event that isn't the caller's). **Never call
`POST /applications/{id}/stage` as a side effect of anything in this section from new code** — the
only place a recruitment-email suggestion may change a real stage is `confirm`, below, which itself
just calls the existing Phase 5 stage service. See ARCHITECTURE.md for the full data-flow diagram
and PRIVACY.md for what is/isn't retained from a message.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/email-tracking/providers` | `ProviderAvailabilityOut` — `gmail_available`/`outlook_available`/`forward_email_available` (each `true` only when its feature flag is on **and** its credentials are configured — always `false` for Gmail/Outlook in this environment) plus `forward_email_alias` when forwarding is available. Backs the settings screen's "Connect" vs. "In Development" provider cards. |
| GET | `/api/v1/email-tracking/connections` | The caller's non-disconnected connections. Response schema (`EmailConnectionOut`) has **no token field at all** — not even encrypted. |
| POST | `/api/v1/email-tracking/gmail/connect` | Generates a single-use OAuth `state` bound to (user, GMAIL), returns `{"authorization_url"}`. 503 if Gmail tracking isn't available in this environment (see `providers` above) — never a crash. |
| GET | `/api/v1/email-tracking/gmail/callback` | Hit directly by the browser after Google's consent screen (`?code=&state=`) — no bearer token on this request; the `state` is what recovers the CareerOS user. Rejects an unknown/expired/already-consumed state with 400. Exchanges the code, encrypts and stores the tokens, establishes a Gmail watch. |
| POST / GET | `/api/v1/email-tracking/outlook/connect` / `/outlook/callback` | Same shape as the Gmail pair, for Microsoft/Outlook. |
| DELETE | `/api/v1/email-tracking/connections/{id}` | Disconnect: best-effort provider-side revoke, clears the stored (encrypted) tokens, marks the connection `DISCONNECTED`. Confirmed application timeline history is never touched. |
| DELETE | `/api/v1/email-tracking/data` | Spec §35 — deletes the caller's `recruitment_email_events` rows only (`{"deleted_events": <count>}`). Confirmed `ApplicationStageEvent` rows are untouched — they live on `applications`, not here. |
| GET | `/api/v1/email-tracking/events` | Optional `?application_id=` to scope to one application (backs the application detail "Emails" tab, spec §32). |
| GET | `/api/v1/email-tracking/events/{id}` | Full detail including `classification_reason_json`'s evidence list (spec §29's "Detected because..." explainability). |
| POST | `/api/v1/email-tracking/events/{id}/confirm` | **The only endpoint in this codebase that may change `current_stage` on behalf of a recruitment email.** 404 if the event or its matched application isn't the caller's; 409 if already confirmed/ignored; 422 if no application is matched yet or no stage was detected. Calls `ApplicationService.update_stage(..., source="EMAIL_CONFIRMED", commit=False)` and marks the event `CONFIRMED` in one transaction, committing once — either both happen or neither does. |
| POST | `/api/v1/email-tracking/events/{id}/ignore` | Marks `IGNORED`. 409 if already confirmed/ignored. |
| POST | `/api/v1/email-tracking/events/{id}/assign-application` | Body: `application_id`, which **must** be one of the event's own `candidate_application_ids` (spec §25 — never accepts an arbitrary application, never guesses). Resolves an `AMBIGUOUS` event to `SUGGESTED`. |
| GET | `/api/v1/email-tracking/events/{id}/prep-hint` | `{"prep_flow": "aptitude" \| "interview" \| null}` — lets the mobile client offer "Prepare for Aptitude Test"/"Prepare for Interview" after a confirm, reusing the Phase 6/7 flows (spec §30/§62) rather than building a duplicate one. |
| POST | `/api/v1/webhooks/gmail` | Google Pub/Sub push-subscription endpoint. Validates the expected topic when `GOOGLE_PUBSUB_TOPIC` is configured, finds the connection matching the notified mailbox (an unknown/inactive mailbox is a quiet 204, never an error), enqueues a history sync. Never classifies anything before returning to the caller. |
| POST | `/api/v1/webhooks/microsoft` | Microsoft Graph change-notification endpoint. Echoes `?validationToken=` verbatim during subscription creation (Graph's required handshake); otherwise enqueues a sync per notified subscription. |
| POST | `/api/v1/webhooks/microsoft/lifecycle` | Graph lifecycle-notification endpoint. Same validation handshake; handles `reauthorizationRequired` (marks the connection), `subscriptionRemoved` (attempts safe resubscription), and `missed` (triggers a reconciliation sync). |

Admin operational metrics for email tracking (spec §64: active watches/subscriptions, reauth-needed
count, events processed/matched/ambiguous, webhook failures) are **not implemented** this phase —
admin web work stayed out of scope, consistent with the Phase 9 boundary every other admin CMS gap
in this file already respects. There is no admin inbox-viewer and none is planned (spec §63).

## Planned endpoint groups (filled in per phase, not yet built)

```
/profile         career preferences, skills, experiences, education, certifications (beyond §10 basics)
/applications    document attachments (CRUD/stage/notes already implemented above)
/documents       CV vault + document vault upload/list/rename/delete (signed URLs, private by default)
/notifications   list, mark read, preferences
/admin/*         news/company-follow publishing, source registry, discovery queue, user management,
                 email-tracking operational metrics (jobs/scholarships/companies/aptitude/interview
                 question-bank admin, and email-tracking connect/webhook endpoints, already
                 implemented above)
```

Each group gets its exact request/response schemas documented here when its phase is implemented —
this file must stay in sync with `app/api/v1/*` and `app/schemas/*`, not drift ahead of the code.

## Scoring transparency

`/ats` and `/jobs/{id}` responses that include a match score must also include a `score_breakdown`
object naming each weighted component (see `ARCHITECTURE.md` → Scoring engines) so the client can
render *why* a score is what it is. Never return a bare percentage with no breakdown.
