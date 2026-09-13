# CareerOS — Database

PostgreSQL, accessed only through the backend via SQLAlchemy 2 (async) + Alembic migrations.
Local dev without Docker/Postgres falls back to SQLite via `DATABASE_URL` in `backend/.env` — schemas
must stay portable between the two (avoid Postgres-only types in early migrations where practical;
JSON/array-heavy columns will need a Postgres-only migration path documented when they land).

## Status

Implemented so far (migrations `1787363de7f0` → `1bee777c8a2b`, `backend/migrations/versions/`):

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
- `applications` — `id`, `user_id` (FK, CASCADE — strictly user-owned, no admin visibility), `job_id`
  (FK → `jobs.id`, `ON DELETE SET NULL` — tracker history survives an expired/deleted job),
  `cv_document_id` (FK, `SET NULL`), `company_name`/`role_title` (denormalized — an application can
  track a role that was never in our `jobs` table at all, spec §36), `location`, `job_url`,
  `current_stage` (19-value enum from spec §36: SAVED → ... → HIRED/REJECTED/WITHDRAWN/EXPIRED/
  NO_RESPONSE), `applied_date`/`deadline`/`interview_date`/`assessment_date`, `salary`, `contact_name`/
  `contact_email`, `cover_letter_text` (plain text, not a file — a real document vault is a later
  phase), `is_demo`.
- `application_stage_events` — `id`, `application_id` (FK, CASCADE), `stage`, `occurred_at`, `note`,
  `source` (`"MANUAL"` always for now — the column exists so Phase 8's email-detection flow can write
  `"EMAIL_CONFIRMED"` later without a schema change). Append-only: created automatically every time
  `current_stage` changes, never edited — the timeline is a true history, not an editable log.
- `application_notes` — `id`, `application_id` (FK, CASCADE), `text`.
- `question_categories` — `id`, `name`, `slug` (unique), `description`. The six fixed sections
  (Numerical/Verbal/Abstract/Logical/Situational Judgement/Technical) — modeled as real rows, not a
  hardcoded enum, so Phase 9's admin UI can rename/describe them without a schema change.
- `question_topics` — `id`, `category_id` (FK, CASCADE), `name`, `slug` (unique), `field`/`industry`
  (nullable — let a Technical topic be scoped, e.g. "Pumps" → Mechanical Engineering/Oil & Gas, so the
  job-specific generation engine can match on them; see `app/aptitude/technical_topic_map.py`).
- `questions` — `id`, `question_text`, `question_type` (`SINGLE_CHOICE`/`MULTIPLE_CHOICE`/`TRUE_FALSE`/
  `NUMERIC`/`IMAGE_BASED`/`PASSAGE_BASED`), `question_image_url`, `passage_text` (repeated verbatim
  across every question sharing a passage — no separate passages table, a documented simplification),
  `category_id` (FK, CASCADE), `topic_id` (FK → `question_topics.id`, `SET NULL`), `field`/`industry`/
  `job_role` (indexed, nullable), `difficulty` (`EASY`/`MEDIUM`/`HARD`/`EXPERT`), `explanation`,
  `marks`/`negative_marks`, `estimated_seconds`, `correct_numeric_value`/`numeric_tolerance` (NUMERIC
  type only), `is_active`, `is_demo`, `created_by_admin_id` (FK, `SET NULL`).
- `question_options` — `id`, `question_id` (FK, CASCADE), `option_text`, `option_image_url`,
  `is_correct`, `display_order`. **Never sent to a mobile client while a test is in progress** — see
  `SessionQuestionOut`/`OptionOut` in `API.md`.
- `test_sessions` — `id`, `user_id` (FK, CASCADE), `mode` (`PRACTICE`/`TIMED`/`MOCK`/`JOB_SPECIFIC`/
  `FIELD_SPECIFIC`/`COMPANY_SPECIFIC` — the last modeled per spec but never exposed in the UI),
  `status` (`CREATED`/`IN_PROGRESS`/`SUBMITTED`/`AUTO_SUBMITTED`/`ABANDONED`; creating a session moves
  it straight to `IN_PROGRESS` — `CREATED` exists for schema completeness only), `application_id`/
  `job_id` (FK, `SET NULL`), `config` (JSON — the exact request that created it, so Retake/Practice
  Similar can reproduce it), `started_at`/`submitted_at`/`expires_at` (all nullable — `expires_at` is
  null for untimed practice), `time_limit_seconds`/`time_used_seconds`, `auto_submitted`,
  `question_count`/`total_marks`, `score`/`percentage`/`correct_count`/`incorrect_count`/
  `unanswered_count` (all null until graded), `section_breakdown` (JSON, computed once at grading time).
- `test_session_questions` — **the critical snapshot table.** A frozen, point-in-time copy of one
  question as shown in one session: `question_text`, `question_type`, `question_image_url`,
  `passage_text`, `difficulty`, `explanation`, `marks`, `negative_marks`, `category_slug`/
  `category_name`, `topic_name`/`topic_slug`, `options_snapshot` (JSON list, deliberately **without**
  `is_correct`), `correct_option_ids` (JSON, server-only grading reference),
  `correct_numeric_value`/`numeric_tolerance`. `question_id` (FK → `questions.id`, `SET NULL`) is kept
  only so "Practice Similar Questions" can jump back to the live topic — it is never re-read for
  grading or display once the snapshot row exists. **Editing or deleting the master `questions` row
  later can never change a past session's questions, answers, or grade** — every field a user saw, or
  that grading depends on, lives in this table, copied at session-creation time.
- `test_answers` — `id`, `session_id` (FK, CASCADE), `session_question_id` (FK →
  `test_session_questions.id`, CASCADE), `selected_option_ids` (JSON)/`answer_numeric_value`,
  `is_flagged`, `time_spent_seconds`, `is_correct`/`marks_awarded` (both null until submit-time
  grading, so "has this been graded" is unambiguous).
- `interview_question_categories` — `id`, `name`, `slug` (unique), `description`. The ten fixed
  categories from spec §6 (hr_general/behavioral/technical/company_specific/job_specific/safety/
  leadership/management/situational/career_motivation) — real rows, same convention as aptitude's
  `question_categories`.
- `interview_topics` — `id`, `category_id` (FK, CASCADE), `name`, `slug` (unique), `field`/
  `industry` (nullable, for job-specific Technical-topic bias — see
  `app/interview/job_role_topic_map.py`).
- `interview_questions` — `id`, `question_text`, `category_id` (FK, CASCADE), `topic_id` (FK,
  `SET NULL`), `field`/`industry`/`job_role` (indexed, nullable), `company_id` (FK →
  `companies.id`, `SET NULL` — **editorial tagging only**, never evidence of a real leaked
  interview question from that employer; see PRIVACY.md), `experience_level` (nullable, reuses
  `jobs.ExperienceLevel`), `difficulty` (`EASY`/`MEDIUM`/`HARD`/`EXPERT`), `answer_guidance` (JSON:
  `{assessing, strong_answer_includes[], common_mistakes[], technical_concepts[]}` — deterministic,
  hand-authored, never AI-generated), `evaluation_points` (JSON list), `follow_up_prompt`,
  `star_tags` (JSON list of STAR category slugs this question matches, for spec §16's suggestion
  feature), `is_active`, `is_demo`, `created_by_admin_id` (FK, `SET NULL`).
- `interview_sessions` — `id`, `user_id` (FK, CASCADE), `mode` (`PRACTICE`/`MOCK`), `status`
  (`IN_PROGRESS`/`COMPLETED`/`ABANDONED`), `application_id`/`job_id`/`company_id` (FK, `SET NULL`),
  `config` (JSON), `categories_requested` (JSON), `time_per_question_seconds` (nullable —
  **self-paced/informational only, never server-enforced**, unlike the aptitude engine's overall
  timer; see ARCHITECTURE.md), `started_at`/`completed_at`, `question_count`.
- `interview_session_questions` — the same snapshot pattern as `test_session_questions`: a frozen
  copy of `question_text`/`category_slug`/`category_name`/`topic_name`/`difficulty`/
  `answer_guidance`/`evaluation_points`/`follow_up_prompt`/`star_tags`/`time_limit_seconds` taken
  at session-creation time, so editing the master question bank later never changes a past
  session. `question_id` (FK, `SET NULL`) is kept only for future "practice similar" navigation.
- `interview_answers` — `id`, `session_id` (FK, CASCADE), `session_question_id` (FK, CASCADE),
  `answer_text`/`notes`, `audio_path`/`audio_duration_seconds` (local file reference only — the
  binary is never uploaded to this backend, see PRIVACY.md), `self_rating` (1-5, **user-declared**,
  never system-computed), `used_star`/`gave_measurable_result`/`answered_exact_question` (all
  **user self-rated** booleans), `is_skipped`/`is_marked_practiced`/`is_saved`, `word_count`
  (**system-computed** deterministically from `answer_text` at save time).
- `star_stories` — `id`, `user_id` (FK, CASCADE), `title`, `category` (14-value `StarCategory` enum
  from spec §14), `situation`/`task`/`action`/`result`/`lessons` (free text), `skills_demonstrated`/
  `relevant_roles`/`relevant_questions` (JSON lists), `metrics`, `company_context`. Completeness
  (spec §15) is **never stored** — it's recomputed deterministically from the four STAR fields on
  every read (`app/interview/star_check.py`), so it can never go stale relative to edits.
- `interview_preparation_progress` — `id`, `user_id` (FK, CASCADE), `application_id` (FK, CASCADE,
  nullable — `NULL` is the general, non-application-linked progress row), `checklist` (JSON dict of
  the 7 fixed company-research items from spec §26), `questions_to_ask` (JSON list of
  `{id, text, category, status, is_custom}` — the curated catalog from spec §27 plus any
  user-added custom questions), `reviewed_topics` (JSON list of technical topic slugs the user has
  marked reviewed, reusing the aptitude engine's topic taxonomy by slug only — no FK coupling
  between the two engines).

### Phase 7.5 additions (migration `1bee777c8a2b`)

- `questions.question_image_alt_text` / `question_options.option_image_alt_text` — nullable
  `String(500)`. Written as a neutral structural description, never one that reveals which option
  is correct (see ARCHITECTURE.md). Snapshotted into `test_session_questions.question_image_alt_text`
  and `options_snapshot`'s `option_image_alt_text` field exactly like every other question attribute.
- `test_session_questions.question_image_alt_text` — the frozen, per-session copy (see above).
- `star_stories.version` / `interview_preparation_progress.version` — `Integer NOT NULL DEFAULT 1`,
  incremented on every server-side write. Used for optimistic-concurrency conflict detection: an
  update carrying a stale `expected_version` is rejected with 409 rather than applied (see
  ARCHITECTURE.md → "Offline-conflict versioning").
- `media_assets` — `id`, `storage_key`, `url`, `mime_type`, `width`/`height` (nullable), `file_size`,
  `alt_text` (nullable), `created_at`/`updated_at`. One row per upload through the shared image
  pipeline (`POST /admin/uploads/image`) — an audit/metadata record, not a binary store; the file
  itself lives on disk (dev) or object storage (future), never duplicated into Postgres.
- `interview_recordings` — `id`, `user_id` (FK → `users.id`, CASCADE), `session_id` (FK →
  `interview_sessions.id`, CASCADE), `session_question_id` (FK → `interview_session_questions.id`,
  CASCADE), `local_path` (a string meaningful only on the originating device — **never** a server
  file path; the audio itself never reaches this backend), `duration_seconds`, `title` (nullable),
  `upload_status` (`"local_only"` always, for now — no upload code path exists; see PRIVACY.md and
  ARCHITECTURE.md). Indexed on `user_id`/`session_id`/`session_question_id`.

Everything else below is the **target** schema from the master spec, not yet implemented. This file
tracks it so later phases implement against a single source of truth instead of re-deriving it.

## Entity groups (target — filled in phase by phase)

```
career_preferences, skills, user_skills, experiences, educations, certifications, projects

job_skills, job_sources

scholarship_requirements (folded into scholarships' own columns for now — see above)

documents (general document vault — cv_documents/ats_analyses already implemented, see above)

application_documents (applications/application_stage_events/application_notes already implemented,
see above — this is just the file-attachment side, blocked on the general document vault)

email_connections, recruitment_email_events

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
