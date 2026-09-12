# CareerOS — Database

PostgreSQL, accessed only through the backend via SQLAlchemy 2 (async) + Alembic migrations.
Local dev without Docker/Postgres falls back to SQLite via `DATABASE_URL` in `backend/.env` — schemas
must stay portable between the two (avoid Postgres-only types in early migrations where practical;
JSON/array-heavy columns will need a Postgres-only migration path documented when they land).

## Status

Implemented so far (migrations `1787363de7f0` → `e4a80fc268db`, `backend/migrations/versions/`):

- `users` — `id` (uuid str pk), `email` (unique, indexed), `hashed_password` (argon2), `is_active`,
  `is_verified`, `created_at`, `updated_at`.
- `profiles` — `id`, `user_id` (FK → `users.id`, unique, `ON DELETE CASCADE`), `full_name`,
  `profile_picture_url`, `professional_title`, `location`, `years_of_experience`,
  `highest_education`, `field_of_study`, `created_at`, `updated_at`. Created empty at registration
  time; the full field set from spec §10 (industries, target roles, preferred countries, etc.) is not
  modeled yet — added when the profile-setup wizard is built.
- `admin_users` — separate table from `users` (never merged — see ARCHITECTURE.md). `id`, `email`
  (unique), `hashed_password`, `role` (`SUPER_ADMIN`/`ADMIN`/`EDITOR`/`REVIEWER`), `is_active`. No
  public self-registration endpoint; first admin is created via `ADMIN_SEED_EMAIL`/`ADMIN_SEED_PASSWORD`
  env vars at startup (`ensure_seed_admin`, no-op once any admin exists).
- `companies` — `id`, `name`, `slug` (unique), `logo_url`, `banner_url`, `website_url`, `career_url`,
  `industry`, `headquarters`, `country`, `description`, `is_verified`, `is_active`.
- `jobs` — `id`, `company_id` (FK → `companies.id`, `ON DELETE CASCADE`), `title`, `slug` (unique),
  location/city/country, `employment_type`/`work_mode`/`experience_level` (Postgres enums via Python
  `str, Enum`), `industry`, `salary_min`/`salary_max`/`salary_currency`/`salary_period`,
  `short_summary`/`description`/`responsibilities`/`requirements`/`preferred_skills`/`benefits` (the
  last four are JSON string-list columns), `thumbnail_url`/`post_image_url`/`image_alt_text`,
  `application_url`/`application_email`/`application_instructions`, `source_type`/`source_url`/
  `source_published_at`, `published_at`/`application_deadline`/`expires_at`, `is_verified`/
  `is_featured`/`is_urgent`/`is_active`/`is_demo`, `status` (`DRAFT`/`REVIEW`/`PUBLISHED`/`EXPIRED`/
  `ARCHIVED`), `created_by_admin_id` (FK → `admin_users.id`, `ON DELETE SET NULL` — deleting the admin
  who created a job must not delete the job). `published_at` is set automatically the first time a job
  transitions to `PUBLISHED` and never overwritten by a later unpublish/republish.
- `saved_jobs` — `id`, `user_id` (FK → `users.id`, CASCADE), `job_id` (FK → `jobs.id`, CASCADE).
- `scholarships` — same shape/lifecycle pattern as `jobs` (see `app/models/scholarship.py`), with
  `organization` as a plain string (no FK to `companies` — scholarship providers are usually not
  companies with career pages) and scholarship-specific fields: `degree_levels`/`fields_of_study`
  (JSON lists), `funding_type` (`FULLY_FUNDED`/`PARTIAL`), funding-coverage strings (tuition/stipend/
  travel/insurance/accommodation), and eligibility fields (`eligible_nationalities`,
  `academic_requirements`, `experience_requirements`, `language_requirements`, `age_requirement`,
  `required_documents` — all JSON lists except `age_requirement`).
- `saved_scholarships` — mirrors `saved_jobs`.
- `cv_documents` — `id`, `user_id` (FK, CASCADE), `name`, `original_filename`, `extracted_text` (plain
  text pulled from the uploaded PDF/DOCX/TXT at upload time — the binary file itself isn't stored),
  `is_primary` (only one CV per user can be primary; enforced in `CvRepository`, not a DB constraint).
- `ats_analyses` — `id`, `user_id` (FK, CASCADE), `cv_document_id` (FK → `cv_documents.id`,
  `ON DELETE SET NULL` — deleting a CV keeps analysis history), `job_id` (FK → `jobs.id`,
  `ON DELETE SET NULL`), `job_description_text` (only set when analyzed against pasted text rather
  than a real job), `job_title`, `overall_score`, `score_breakdown` (JSON: each of the 8 weighted
  components with its own score+weight — see ARCHITECTURE.md), `strong_matches`/`missing_keywords`/
  `formatting_issues` (JSON string lists), `missing_metrics_note`.
- `company_follows` — `id`, `user_id` (FK, CASCADE), `company_id` (FK, CASCADE).
- `intelligence_posts` — `id`, `company_id` (FK → `companies.id`, `ON DELETE SET NULL` — a post can
  outlive the company record, or be company-agnostic industry news), `headline`, `slug` (unique),
  `category` (13-value enum from spec §19: LEADERSHIP/TECHNOLOGY/AUTOMATION/.../GRADUATE_RECRUITMENT),
  media fields, `summary`/`full_content`, `why_it_matters` (admin-written, never generated — see
  ARCHITECTURE.md), `relevant_roles`/`relevant_skills` (JSON lists), source fields, `published_at`,
  verification/featured/active/demo flags, `status`, `created_by_admin_id`.

Everything else below is the **target** schema from the master spec, not yet implemented. This file
tracks it so later phases implement against a single source of truth instead of re-deriving it.

## Entity groups (target — filled in phase by phase)

```
career_preferences, skills, user_skills, experiences, educations, certifications, projects

job_skills, job_sources

scholarship_requirements (folded into scholarships' own columns for now — see above)

documents (general document vault — cv_documents/ats_analyses already implemented, see above)

applications, application_stage_events, application_notes, application_documents

email_connections, recruitment_email_events

questions, question_options, question_categories, question_topics

test_sessions, test_answers, test_results

interview_questions, interview_sessions, star_stories

notifications

content_sources, discovered_items

audit_logs
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
- Money/funding amounts stored as integers + ISO currency code, never floats. Exception: `jobs.salary_min`/
  `salary_max` are stored as whole-currency-unit integers (not minor units) — salary ranges don't need
  cent precision, and it keeps admin-side editing simple (no ×100/÷100 anywhere in the CMS form).
