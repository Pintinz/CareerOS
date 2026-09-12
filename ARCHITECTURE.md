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

## Aptitude assessment engine (`app/aptitude/`, Phase 6)

Also deterministic/rules-based, not AI:

- **Generation** (`app/aptitude/generator.py`) — samples the requested count of active questions from
  the requested categories/difficulty. For `MIXED` difficulty, targets a 30/45/20/5 (easy/medium/hard/
  expert) split and backfills any shortfall from other difficulties rather than erroring when the bank
  is thin. Job/field-specific runs bias Technical questions toward relevant topics via a pure keyword
  lookup table (`app/aptitude/technical_topic_map.py` — e.g. "Process Technician" → Pumps, Valves,
  Compressors, P&IDs, DCS, SCADA, ...), falling back to the full category pool if too few topic-matched
  questions exist. "Practice Weak Areas" instead passes an explicit `topic_slugs` override, bypassing
  the job-title inference entirely — same underlying selection code, different topic source.
- **Snapshot-then-grade** — session creation copies every selected question's full content into
  `test_session_questions` (see `DATABASE.md`). This is the single mechanism that satisfies "editing a
  question later must never change a past session": nothing at grading/review time re-reads the live
  `questions` table.
- **Timer authority** — `expires_at` is a server timestamp, not a client-side countdown. Every session
  read/mutate call in `AptitudeService` first checks whether `expires_at` has passed and, if so, grades
  and closes the session inline (a "lazy auto-submit," not a background job — this stack has no
  Celery/APScheduler wired up yet) before doing anything else. A client can never keep answering, or
  keep a session alive, past its expiry just by not calling submit.
- **Grading** (`app/services/aptitude_service.py`) — per-question-type: choice questions (including
  `IMAGE_BASED`/`PASSAGE_BASED`, which are graded as single-choice — a documented simplification, since
  the spec's question-type enum conflates presentation with response mechanism) by exact selected-
  option-set match; `NUMERIC` by tolerance comparison. Overall score is marks-weighted (respects
  `marks`/`negative_marks`); `section_breakdown` is a simple per-category accuracy percentage — a
  deliberate, documented difference in aggregation style from the marks-weighted overall score, chosen
  to match the spec's plain-language "Numerical 87%" example.
- **Performance labels** are threshold-based ("Strong Performance" / "Good Performance" / "Needs
  Improvement"), never a random pass/fail, with thresholds centralized in `app/aptitude/scoring.py`.
  Weak-topic recommendations require a minimum of 3 attempted questions in a topic before that topic's
  accuracy is used, to avoid drawing conclusions from a tiny sample.

## Mobile aptitude offline behavior (`mobile/lib/features/aptitude/`)

Once a test session is loaded, it must survive a temporary connectivity loss or the app being
backgrounded/restarted (spec §20-21):

- `AptitudeOfflineCache` (SharedPreferences-backed — see note below) mirrors the full session detail
  (questions, options, current answers/flags, `expires_at`) to local storage on every load and every
  successful sync, and a pending-mutation queue for answers/flags made while offline.
- `ExamController` loads from the server first; if that fails and a cached session already exists, it
  keeps working from the cache rather than blocking the user with an error screen, flagging
  `hasUnsyncedChanges` so the UI can show an honest "not synced yet" indicator. Pending mutations are
  replayed opportunistically (on load, and before every new mutation) rather than via a connectivity-
  listener package.
- The countdown timer is computed from `expires_at` and a one-time device-clock-to-server-clock offset
  captured at load time, re-evaluated every second — never a bare `Timer` counting down from a fixed
  duration, so an app restart mid-test resumes with the correct remaining time. The backend's own lazy
  auto-submit check is still the actual authority; the client timer only decides when to *call* submit.
- This uses `SharedPreferences` (already the app's local key-value store — see `AppPreferences`)
  rather than the `drift` SQLite dependency declared in `pubspec.yaml`, which nothing in this codebase
  actually wires up yet (no generated database exists anywhere in `mobile/lib`). A single JSON blob per
  active session is a proportionate amount of local-storage machinery for this one feature; introducing
  a full Drift schema for it would be disproportionate scope. Worth revisiting if a future phase needs
  genuine relational local storage (e.g. an offline job feed) — at that point migrating this cache onto
  the same mechanism becomes worthwhile.

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
