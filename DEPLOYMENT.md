# CareerOS — Deployment

## Local development

See `README.md` → Quick start. Summary:

- Backend: Python venv + `uvicorn app.main:app --reload`, SQLite fallback if `DATABASE_URL` is unset
  or Postgres/Docker is unavailable.
- Admin: `npm run dev` (Next.js dev server, port 3000).
- Mobile: requires Flutter SDK + Android SDK + a JDK. See "Mobile toolchain setup" below.
- Full stack: `docker compose up` (requires Docker Desktop — not installed on the reference dev
  machine as of Phase 0).

## Mobile toolchain setup (Windows)

Verified working combination for Flutter 3.47.4 on this project (as of this writing):

1. **Flutter SDK**: download the stable Windows zip from
   https://docs.flutter.dev/get-started/install/windows and extract to e.g. `C:\flutter`.
2. **JDK 17**: use a **zip distribution** (e.g. Eclipse Temurin), not the installer. An MSI-based
   JDK installer run non-interactively can hang indefinitely waiting on a UAC elevation prompt with
   no one to answer it — this happened during initial setup and had to be killed and replaced with
   the zip approach. Extract to e.g. `C:\jdk17`.
3. **Android SDK**: download "Command line tools only" from
   https://developer.android.com/studio#command-line-tools-only (do not need full Android Studio for
   CLI builds). Extract so the layout is `<ANDROID_HOME>\cmdline-tools\latest\...` (the zip extracts to
   a `cmdline-tools` folder that must be renamed/moved to `latest`). Then:
   ```bash
   sdkmanager.bat --licenses          # accept all
   sdkmanager.bat "platform-tools" "platforms;android-36" "build-tools;28.0.3"
   ```
   Flutter 3.47.4 specifically wants Android SDK 36 + Build-Tools 28.0.3 — `flutter doctor -v` names
   its current required versions explicitly if these are ever out of date for a newer Flutter release.
4. Set environment variables (System Properties → Environment Variables, for a permanent setup):
   - `JAVA_HOME` = the JDK folder (e.g. `C:\jdk17\jdk-17.0.20.1+1`)
   - `ANDROID_HOME` / `ANDROID_SDK_ROOT` = the SDK folder (e.g. `C:\Android`)
   - Add to `PATH`: `%JAVA_HOME%\bin`, `C:\flutter\bin`, `%ANDROID_HOME%\cmdline-tools\latest\bin`,
     `%ANDROID_HOME%\platform-tools`
   - Then: `flutter config --android-sdk C:\Android` and `flutter doctor -v` to confirm.
5. Verify with, in order: `flutter pub get`, `flutter analyze`, `flutter test`,
   `flutter build apk --debug` (see `PROJECT_STATUS.md` for this project's actual results).
6. iOS builds require a Mac with Xcode — cannot be done or verified on Windows at all.

### Known transient failure: Maven Central 403s during `flutter build apk` (Phase 7.5)

Adding `permission_handler` pulled in `permission_handler_android`, whose own `build.gradle`
declares a legacy `buildscript { classpath 'com.android.tools.build:gradle:8.0.0' }` block — AGP
8.0.0's own transitive tree includes `io.grpc:grpc-netty` (and its netty/guava/httpcore
dependencies), which Maven Central intermittently answered with `403 Forbidden` for a handful of
artifacts per attempt during this session's build (each individual artifact was reachable via a
direct `curl`, so this reads as upstream rate-limiting rather than a real block). Simply retrying
`flutter build apk --debug` a few times let Gradle's dependency cache fill in incrementally until a
full resolution succeeded — no project configuration change was needed for this part. If it recurs
persistently, `gradle.properties` → `systemProp.http(s).proxyHost`/retry tuning, or a Gradle mirror
repository, would be the next thing to try — not attempted here since retrying resolved it.

### Real fix required: `record` package version bump (Phase 7.5)

`record: ^5.2.0` (the initial constraint added for interview audio recording) resolves an old
`record_linux` (0.7.2) that does not implement the newer `record_platform_interface` (1.6.0) that
another transitive dependency pulls in — a genuine version-matrix inconsistency in that release of
the `record` package, unrelated to any platform this app actually ships (Android/iOS), but still
fatal to compilation since Flutter compiles every federated platform implementation regardless of
target. **Fix**: bump the constraint to `record: ^7.1.1` in `mobile/pubspec.yaml` and re-run
`flutter pub get` — this resolves a consistent `record_platform_interface 2.1.0` across every
platform package. No `RecordingService` code changes were required; `flutter analyze`/`flutter test`
were clean both before and after the bump.

## Environment variables

Never commit real secrets. Each app ships a `.env.example`; copy to `.env` (`admin` uses `.env.local`)
and fill in locally. Production secrets are injected by the hosting platform's secret manager, never
checked into source control.

Backend (`backend/.env.example`): `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`,
`ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `CORS_ORIGINS`, `ENVIRONMENT`,
`GOOGLE_CLIENT_ID` (optional), `APPLE_CLIENT_ID` (optional), `ADMOB_APP_ID` (optional), `REDIS_URL`
(optional), plus the Phase 8 email-tracking variables documented below (all optional — the feature
runs on a mock provider with none of them set).

Admin (`admin/.env.example`): `NEXT_PUBLIC_API_BASE_URL`, `ADMIN_SESSION_SECRET`. Note:
`ADMIN_SESSION_SECRET` is not currently read anywhere in the admin app's code (it stores its JWT
in `localStorage`, not a server-side session) — it's a leftover placeholder from an earlier design,
not an active secret. Harmless but worth removing or actually wiring up before relying on it.

**Phase 9.5 audit hardening**: the backend now refuses to start with `ENVIRONMENT=production` if
`JWT_SECRET_KEY` or `TOKEN_ENCRYPTION_KEYS` are still set to their publicly-committed dev-only
default values (or an obvious `change-me`-style placeholder) — see `app/core/config.py`'s
`uses_insecure_defaults` and `app/main.py`'s `lifespan`. This was a real gap before this phase:
nothing previously stopped a misconfigured production deployment from silently running with a
secret anyone with access to this repository already knows. **This guard has only been exercised
by unit tests of `Settings.uses_insecure_defaults`** — it has never been tested against an actual
production-configured deployment, since none exists in this environment. Verify it behaves as
expected the first time a real production environment is stood up.

Mobile: `mobile/lib/config/env.dart` reads compile-time `--dart-define` values (API base URL, AdMob
unit IDs) — no `.env` file is bundled into the app binary.

## Smart Recruitment Email Tracking — production setup (Phase 8)

None of this is done in this environment — no Google Cloud project, Microsoft Entra app
registration, or Pub/Sub topic exists here. Everything below is what a real deployment needs before
Gmail/Outlook tracking can be anything more than mock-verified. See ARCHITECTURE.md for how the
code uses each of these, and PRIVACY.md for what's actually done with the access once granted.

### Gmail

1. Create (or reuse) a Google Cloud project; enable the **Gmail API**.
2. Configure the **OAuth consent screen** — scope `https://www.googleapis.com/auth/gmail.readonly`
   only. **A commercial public release using this scope may require Google's OAuth verification
   and, depending on the consent screen's publishing status and CareerOS's server-side handling of
   this restricted-scope data, an additional security assessment** — this is a deployment/compliance
   requirement Google imposes, not a code bug, and is not something this session can complete
   without a real Google Workspace/Cloud identity. Budget real calendar time for it before a public
   launch that uses Gmail tracking.
3. Create an **OAuth 2.0 client ID** (type: Web application) — set its authorized redirect URI to
   `GOOGLE_REDIRECT_URI` (the backend's `/api/v1/email-tracking/gmail/callback` URL, publicly
   reachable). Set `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` from it.
4. Create a **Cloud Pub/Sub topic** for Gmail push notifications; grant the special Gmail service
   account (`gmail-api-push@system.gserviceaccount.com`) the **Pub/Sub Publisher** role on that
   topic. Set `GOOGLE_PUBSUB_TOPIC` to its full resource name
   (`projects/<project>/topics/<topic>`).
5. Create a **Pub/Sub push subscription** on that topic pointing at the backend's
   `POST /api/v1/webhooks/gmail` endpoint (publicly reachable, HTTPS).
6. Once a connection exists, `users.watch` (called automatically on connect, see
   `EmailTrackingService.handle_oauth_callback`) registers the mailbox against that topic — this
   expires (roughly every 7 days) and must be renewed; see "Watch/subscription renewal worker"
   below.
7. Production hardening this codebase does **not** yet implement: verifying the Pub/Sub push
   request's JWT (Google signs each push request; the current webhook only validates the topic name
   found inside the message envelope, not the request's own signature) — add JWT audience/issuer
   verification before relying on this in production, per Google's Pub/Sub push-authentication docs.

### Outlook / Microsoft 365

1. Register an app in **Microsoft Entra ID** (formerly Azure AD) — supported account type
   "Accounts in any organizational directory and personal Microsoft accounts" if consumer accounts
   should work too (matches this codebase's default `MICROSOFT_TENANT=common`).
2. Add a **Web** platform redirect URI matching `MICROSOFT_REDIRECT_URI` (the backend's
   `/api/v1/email-tracking/outlook/callback`).
3. Add delegated Microsoft Graph permissions: `Mail.Read`, `User.Read`, `offline_access` only — no
   `Mail.ReadWrite`, no application (non-delegated) permissions of any kind.
4. Create a client secret; set `MICROSOFT_CLIENT_ID`/`MICROSOFT_CLIENT_SECRET`.
5. Expose two publicly reachable HTTPS endpoints for Graph change notifications: set
   `MICROSOFT_WEBHOOK_URL` to `POST /api/v1/webhooks/microsoft` and
   `MICROSOFT_LIFECYCLE_WEBHOOK_URL` to `POST /api/v1/webhooks/microsoft/lifecycle`. Graph will call
   the webhook URL with a `?validationToken=` during subscription creation — already implemented
   (echoed back as plain text, see `app/api/v1/webhooks.py`).
6. Graph mail subscriptions cap at roughly 4230 minutes (~3 days); this codebase's
   `establish_watch`/`renew_watch` request 2 days deliberately, leaving headroom before expiry.

### Watch/subscription renewal worker (now scheduled — Phase 9)

`EmailTrackingService.renew_expiring_watches()` now runs automatically every 24 hours via the
in-process APScheduler wired into `app/scheduler.py`'s FastAPI `lifespan` — no separate worker
process is required for a single-instance deployment. **This scheduler runs inside the API process
itself**, so a multi-instance/horizontally-scaled production deployment must ensure only one
instance actually runs the scheduled jobs (e.g. gate `start_scheduler()` behind a leader-election
flag, an environment variable set on exactly one instance, or move it to a dedicated worker process)
— running it on every instance would renew/publish/expire redundantly, which is wasteful but not
unsafe (every job is idempotent) unless the redundant calls trip a provider's rate limit.

### Background job scheduler and queue

`app/scheduler.py` also runs scheduled content publishing (15min) and content expiration (1h) on the
same in-process scheduler. `app/services/background_tasks.py`'s `InlineTaskRunner` still executes
webhook-triggered processing synchronously, in-process — fine for development and low volume, but a
production deployment handling real webhook traffic should implement a `BackgroundTaskRunner` backed
by whatever queue is already chosen for the rest of the platform (Celery/RQ/cloud tasks) and swap it
in; no webhook route needs to change to make that swap. Source-discovery polling is not scheduled at
all — no ingestion adapter exists yet (see PROJECT_STATUS.md's Phase 9 section); wiring one in would
also mean adding it to the scheduler here.

### Admin seed account

`ensure_seed_admin()` (in `app/main.py`'s `lifespan`) creates the first `SUPER_ADMIN` from
`ADMIN_SEED_EMAIL`/`ADMIN_SEED_PASSWORD` on first run only — it is a no-op if either is unset or if
any admin already exists (never overwrites/resets an existing account). Set both in production for
exactly long enough to create the real first admin, then either unset them or rotate that account's
password immediately — they stay effective as a "create if missing" trigger on every subsequent
restart otherwise.

## Android build (once Flutter is installed)

```bash
cd mobile
flutter build appbundle --release
```

Requires: package ID configured, adaptive icon, release keystore (documented separately, never
committed), AdMob app ID in `AndroidManifest.xml` via `--dart-define` or Gradle property.

## iOS build (once Flutter is installed, on macOS with Xcode)

```bash
cd mobile
flutter build ipa --release
```

Requires: bundle identifier, signing team in Xcode, `Info.plist` privacy usage strings (photo library,
camera, microphone, notifications), Sign in with Apple capability enabled in the Apple Developer portal.

## Database migrations

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

Never hand-edit a migration that has already been applied to a shared environment — create a new one.

## Rollout order for future environments (staging/prod)

1. Provision Postgres (managed, e.g. RDS/Cloud SQL) — not the Docker Compose instance.
2. Deploy backend, run `alembic upgrade head` against it.
3. Deploy admin, pointed at the backend's public URL.
4. Ship mobile builds pointed at the backend's public URL via `--dart-define`.

Not yet built: CI/CD pipeline definitions, infra-as-code, production secret manager wiring — these
belong to Phase 11 (Production Hardening) and are out of scope until earlier phases are functionally
complete.
