# CareerOS — Architecture

## Overview

Three deployable applications share one PostgreSQL database (accessed only by the backend):

```
┌─────────────┐        ┌──────────────┐        ┌────────────────┐
│  Flutter    │  HTTPS │   FastAPI    │  SQL   │   PostgreSQL    │
│  mobile app │ ─────► │   backend    │ ─────► │   database      │
└─────────────┘        └──────┬───────┘        └─────────────────┘
                               │ HTTPS (admin-only endpoints, RBAC)
                        ┌──────▼───────┐
                        │  Next.js     │
                        │  admin portal│
                        └──────────────┘
```

- The mobile app and the admin portal both talk to the **same backend**, never to the database directly.
- Admin-only routes live under `/api/v1/admin/*` and require an `admin_users` JWT with role claims
  (`SUPER_ADMIN`, `ADMIN`, `EDITOR`, `REVIEWER`). Consumer routes under `/api/v1/*` use a separate
  `users` JWT. The two token types are not interchangeable.
- All external integrations (Google/Apple Sign-In, Gmail/Outlook OAuth, AdMob, push notifications) are
  implemented behind an interface with a mock/dev provider, selected via environment configuration, so
  the product runs fully in dev without any of those credentials (spec Rule 3).

## Backend layering (`backend/app/`)

```
api/          FastAPI routers — request/response only, no business logic
schemas/      Pydantic request/response models
services/     business logic (matching engine, ATS scoring, email classifier, etc.)
repositories/ SQLAlchemy queries, one repository per aggregate
models/       SQLAlchemy ORM models
security/     password hashing, JWT issuance/verification, RBAC dependencies
workers/      background jobs (APScheduler/Celery) — ingestion, digest emails, expiry sweeps
ingestion/    source adapters (RSS, Lever, Ashby) feeding the discovery queue
matching/     deterministic scoring: job match, ATS readiness, scholarship eligibility
```

Rule: routers depend on services, services depend on repositories, repositories depend on models.
Never skip a layer (a router must not construct raw SQL queries).

## Mobile layering (`mobile/lib/`)

Feature-first clean architecture. Each folder under `features/<name>/` follows:

```
data/         DTOs, remote/local data sources
domain/       entities, repository interfaces, use cases
presentation/ screens, widgets, Riverpod providers/controllers
```

Cross-cutting concerns live in `core/` (networking, storage, utils) and are the only things a feature
is allowed to import from outside its own folder (plus `theme/`, `routing/`, `widgets/`).

## Scoring engines (deterministic, not AI)

Three engines compute their scores from explicit, documented weights stored in backend config
(`app/matching/`), never from an LLM and never randomly:

1. **Job Match Score** — role/title similarity, skill overlap, industry, experience level, location,
   work-mode preference, education, keyword similarity (TF-IDF/cosine where useful).
2. **ATS Readiness Score** — **implemented** (`app/matching/ats_engine.py`), weights in
   `app/matching/ats_weights.py` (keyword coverage 25%, technical skills 20%, experience 20%,
   job title 10%, formatting 10%, education 5%, completeness 5%, placement 5% — see `API.md`).
   Keyword extraction is frequency-ranked unigrams/bigrams (`app/matching/text_utils.py`), with a
   small explicit synonym table (`app/matching/synonyms.py`, e.g. PLC ↔ "programmable logic
   controller") so a CV and JD using different wording for the same concept still match. Every
   response includes the full per-component breakdown, never a bare percentage.
3. **Scholarship Eligibility Match** — not yet implemented. Nationality, degree, field, academic
   level, experience, age, language, test requirements, country eligibility — expressed as
   ✓ / △ / ✕ per criterion, never as a blanket "you are eligible."

All three must describe themselves accurately as rules/similarity-based, per spec Rule 8 (no fake AI).

## Recruitment email classification

Deterministic rule-based keyword/phrase classifier (`app/services/email_classifier.py`), not an LLM
call to an external API. Confidence-scored match against a specific `applications` row using company,
job title, reference number, and timing signals — the app **never** silently changes an application's
stage; it always asks for user confirmation (see `PRIVACY.md`).

## Environment-gated integrations

| Integration | Interface | Mock/dev provider | Real provider needs |
|---|---|---|---|
| Google Sign-In | `AuthProvider` | `MockAuthProvider` | `GOOGLE_CLIENT_ID` |
| Apple Sign-In | `AuthProvider` | `MockAuthProvider` | Apple Developer capability |
| Gmail tracking | `EmailProvider` | `MockEmailProvider` | Google OAuth client + `gmail.readonly` scope |
| Outlook tracking | `EmailProvider` | `MockEmailProvider` | Microsoft Graph app registration |
| AdMob | `AdProvider` | test ad unit IDs | production `ADMOB_APP_ID` |
| Push notifications | `PushProvider` | local-notifications only | FCM server key / APNs cert |

See `PROJECT_STATUS.md` → "Blocked by Credential / Tooling" for current status of each.
