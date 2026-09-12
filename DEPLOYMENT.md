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

## Environment variables

Never commit real secrets. Each app ships a `.env.example`; copy to `.env` (`admin` uses `.env.local`)
and fill in locally. Production secrets are injected by the hosting platform's secret manager, never
checked into source control.

Backend (`backend/.env.example`): `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`,
`ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `CORS_ORIGINS`, `ENVIRONMENT`,
`GOOGLE_CLIENT_ID` (optional), `APPLE_CLIENT_ID` (optional), `GMAIL_OAUTH_CLIENT_ID`/`SECRET`
(optional), `OUTLOOK_OAUTH_CLIENT_ID`/`SECRET` (optional), `ADMOB_APP_ID` (optional), `REDIS_URL`
(optional).

Admin (`admin/.env.example`): `NEXT_PUBLIC_API_BASE_URL`, `ADMIN_SESSION_SECRET`.

Mobile: `mobile/lib/config/env.dart` reads compile-time `--dart-define` values (API base URL, AdMob
unit IDs) — no `.env` file is bundled into the app binary.

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
