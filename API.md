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
| POST | `/api/v1/admin/uploads/image` | admin bearer (EDITOR+) | Multipart `file`. JPG/PNG/WEBP, 8MB max. Returns `{"url": "..."}` served from local disk under `/uploads/*` (spec Rule 3 — swap for a cloud `StorageProvider` later without changing callers). |

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

## Planned endpoint groups (filled in per phase, not yet built)

```
/profile         career preferences, skills, experiences, education, certifications (beyond §10 basics)
/applications    CRUD, stage updates, timeline, notes, documents
/aptitude        section/question selection, test session lifecycle, submit, results, analytics
/interview       question sets, sessions, STAR stories
/documents       CV vault + document vault upload/list/rename/delete (signed URLs, private by default)
/email           connect/disconnect Gmail/Outlook, pending-match confirmation queue
/notifications   list, mark read, preferences
/admin/*         news/company-follow publishing, question bank, source registry, discovery queue,
                 user management (jobs/scholarships/companies admin already implemented above)
```

Each group gets its exact request/response schemas documented here when its phase is implemented —
this file must stay in sync with `app/api/v1/*` and `app/schemas/*`, not drift ahead of the code.

## Scoring transparency

`/ats` and `/jobs/{id}` responses that include a match score must also include a `score_breakdown`
object naming each weighted component (see `ARCHITECTURE.md` → Scoring engines) so the client can
render *why* a score is what it is. Never return a bare percentage with no breakdown.
