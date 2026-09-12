# CareerOS — Deployment

## Local development

See `README.md` → Quick start. Summary:

- Backend: Python venv + `uvicorn app.main:app --reload`, SQLite fallback if `DATABASE_URL` is unset
  or Postgres/Docker is unavailable.
- Admin: `npm run dev` (Next.js dev server, port 3000).
- Mobile: requires Flutter SDK (not installed on the reference dev machine as of Phase 0 — see
  `PROJECT_STATUS.md`).
- Full stack: `docker compose up` (requires Docker Desktop — not installed on the reference dev
  machine as of Phase 0).

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
