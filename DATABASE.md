# CareerOS — Database

PostgreSQL, accessed only through the backend via SQLAlchemy 2 (async) + Alembic migrations.
Local dev without Docker/Postgres falls back to SQLite via `DATABASE_URL` in `backend/.env` — schemas
must stay portable between the two (avoid Postgres-only types in early migrations where practical;
JSON/array-heavy columns will need a Postgres-only migration path documented when they land).

## Status

Implemented so far (migration `1787363de7f0`, `backend/migrations/versions/`):

- `users` — `id` (uuid str pk), `email` (unique, indexed), `hashed_password` (argon2), `is_active`,
  `is_verified`, `created_at`, `updated_at`.
- `profiles` — `id`, `user_id` (FK → `users.id`, unique, `ON DELETE CASCADE`), `full_name`,
  `profile_picture_url`, `professional_title`, `location`, `years_of_experience`,
  `highest_education`, `field_of_study`, `created_at`, `updated_at`. Created empty at registration
  time; the full field set from spec §10 (industries, target roles, preferred countries, etc.) is not
  modeled yet — added when the profile-setup wizard is built.

Everything else below is the **target** schema from the master spec, not yet implemented. This file
tracks it so later phases implement against a single source of truth instead of re-deriving it.

## Entity groups (target — filled in phase by phase)

```
users, profiles, career_preferences, skills, user_skills, experiences, educations,
certifications, projects

companies, company_follows

jobs, job_skills, job_sources, saved_jobs

scholarships, scholarship_requirements, saved_scholarships

intelligence_posts

cv_documents, documents, ats_analyses

applications, application_stage_events, application_notes, application_documents

email_connections, recruitment_email_events

questions, question_options, question_categories, question_topics

test_sessions, test_answers, test_results

interview_questions, interview_sessions, star_stories

notifications

content_sources, discovered_items

admin_users, audit_logs
```

## Conventions (apply from the first real migration onward)

- Every table: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at`, `updated_at` (server-side
  defaults), soft-delete via `deleted_at` where records can be user-removed but must be auditable
  (documents, applications) — hard-delete only for account deletion flows (`PRIVACY.md`).
- Foreign keys always indexed. Use `ON DELETE CASCADE` only where the child record has no meaning
  without the parent (e.g. `job_skills` → `jobs`); use `ON DELETE RESTRICT`/`SET NULL` where deleting
  the parent should not silently destroy history (e.g. `application_stage_events` → `applications`
  should cascade, but `applications` → `jobs` should `SET NULL` so tracker history survives an expired
  job post).
- Enums (application stage, content status, source type, etc.) modeled as Postgres `ENUM` types with a
  matching Python `enum.Enum`, not free-text columns.
- `admin_users` is a **separate table** from `users` — never the same table with a role flag — so a
  compromised consumer JWT can never carry admin claims.
- Money/funding amounts stored as integer minor units + ISO currency code, never floats.
