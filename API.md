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

## Planned endpoint groups (filled in per phase, not yet built)

```
/profile         career preferences, skills, experiences, education, certifications (beyond §10 basics)
/jobs            list/search/filter, detail, save/unsave
/scholarships    list/search/filter, detail, eligibility check, save/unsave
/companies       list, detail, follow/unfollow, jobs/news for a company
/intelligence    news feed, detail
/ats             upload CV, analyze against a job description, analysis history
/applications    CRUD, stage updates, timeline, notes, documents
/aptitude        section/question selection, test session lifecycle, submit, results, analytics
/interview       question sets, sessions, STAR stories
/documents       CV vault + document vault upload/list/rename/delete (signed URLs, private by default)
/email           connect/disconnect Gmail/Outlook, pending-match confirmation queue
/notifications   list, mark read, preferences
/admin/*         job/scholarship/news/company publishing, question bank, source registry, discovery
                 queue, user management, RBAC-gated per admin_users role
```

Each group gets its exact request/response schemas documented here when its phase is implemented —
this file must stay in sync with `app/api/v1/*` and `app/schemas/*`, not drift ahead of the code.

## Scoring transparency

`/ats` and `/jobs/{id}` responses that include a match score must also include a `score_breakdown`
object naming each weighted component (see `ARCHITECTURE.md` → Scoring engines) so the client can
render *why* a score is what it is. Never return a bare percentage with no breakdown.
