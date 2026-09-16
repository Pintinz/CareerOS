# Going live — Render backend + downloadable Android app

Two tracks, same first half: the app is useless to a downloader until the backend is reachable on
the internet, because the build currently points at `http://10.0.2.2:8000` (this PC).

| Step | Who |
|---|---|
| 1. Git repository on GitHub | you (needs your GitHub account) |
| 2. Render account + Blueprint deploy | you (card only if you pick a paid plan) |
| 3. Environment values pasted into Render | you (they are secrets) |
| 4. Upload keystore for signing | you (you choose and keep the password) |
| 5. Release APK + AAB built against the live URL | me |
| 6. APK hosted for download | you (GitHub Release) / me (files prepared) |
| 7. Play Console listing | you (account, $25, review) / me (listing copy, graphics, data-safety answers) |

Nothing here needs me to hold a password: Render generates what it can, you paste the rest.

---

## 1. Put the code on GitHub (private is fine)

```bash
git remote add origin https://github.com/<you>/careeros.git
git push -u origin ui-ux-polish
```

Render deploys from a branch — either merge into `main` first, or point Render at `ui-ux-polish`.
`.gitignore` already excludes `.env`, keystores and `key.properties`, so no secret is pushed.

## 2. Deploy the Blueprint

1. render.com → **New** → **Blueprint** → select the repository → Render reads `render.yaml`.
2. It creates: `careeros-api` (Docker), `careeros-admin` (Next.js), `careeros-db` (PostgreSQL 16).
3. It will prompt for the values marked `sync: false` below.

Region is set to `frankfurt` (closest Render region to Nigeria) — change it in `render.yaml` before
the first deploy if you prefer another.

**Free vs paid:** free web services sleep when idle (first request after a nap takes ~30s) and
Render's free PostgreSQL is time-limited by their policy. For real users, switch both web services
and the database to a paid instance in the dashboard — no file change needed.

## 3. Values to paste

Generate the token-encryption key on your machine (it never passes through chat):

```bash
cd backend && .venv/Scripts/python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

| Service | Key | Value |
|---|---|---|
| careeros-api | `TOKEN_ENCRYPTION_KEYS` | the key printed above |
| careeros-api | `PUBLIC_BASE_URL` | `https://careeros-api.onrender.com` (your API's URL) |
| careeros-api | `CORS_ORIGINS` | `https://careeros-admin.onrender.com` (your admin URL) |
| careeros-api | `ADMIN_SEED_EMAIL` | your admin email |
| careeros-api | `ADMIN_SEED_PASSWORD` | a strong password, 12+ characters |
| careeros-admin | `NEXT_PUBLIC_API_BASE_URL` | `https://careeros-api.onrender.com/api/v1` |

`JWT_SECRET_KEY` and `DATABASE_URL` are filled in by Render itself. The API refuses to start in
production with dev defaults or a SQLite database, so a missing value fails loudly instead of
silently running insecurely.

Migrations run automatically on every deploy (`alembic upgrade head` before the server starts).

### After the first deploy

- Open `https://careeros-api.onrender.com/` — it returns the service name.
- Log in to the admin portal with the seed admin, then **change that password** and remove
  `ADMIN_SEED_PASSWORD` from Render.
- Your content is already there: `BOOTSTRAP_CONTENT=true` imports the bundled content pack at
  startup (see below).

## 3a. Your content goes live with the deployment

`backend/data/content_pack/` is a committed snapshot of everything public in the local database:

| | |
|---|---|
| Companies | 85 |
| Opportunities | 203 (192 published) |
| Scholarships | 5 |
| Company intelligence posts | 21 |
| Career sources | 99 (23 polling automatically) |
| Aptitude questions | 171 (+ 666 options) |
| Interview questions | 213 |
| Media files (logos, question images) | 165 |

No user, application, CV, recording or admin row is in it — production starts with real
opportunities and zero personal data, and a test asserts that those tables can never be added to
the pack.

With `BOOTSTRAP_CONTENT=true` (already in `render.yaml`) the API imports it on every start. It is
idempotent: rows are upserted by id, so a redeploy updates content instead of duplicating it. That
repeat also matters on Render, whose filesystem resets on deploy — the pack restores logos and
question images each time.

**Refreshing it later:** run `cd backend && python -m scripts.export_content` here, commit the
changed pack, and the next deploy picks it up. Once you start publishing directly in the live admin
portal, set `BOOTSTRAP_CONTENT=false` so a deploy can't overwrite newer live edits with the
snapshot, and add a Render persistent disk (or S3/Cloudflare R2) for uploads made in production —
otherwise images uploaded through the live admin are lost on the next deploy.

## 4. Create the upload keystore (you)

The keystore identifies you as the publisher for the life of the app. If it's lost, you cannot
update the app on Play. Keep the file and password in your password manager, never in the repo.

```bash
keytool -genkey -v -keystore careeros-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias careeros
```

Then create `mobile/android/key.properties` (already gitignored):

```properties
storeFile=C:/path/to/careeros-upload.jks
storePassword=<your store password>
keyPassword=<your key password>
keyAlias=careeros
```

Without this file, release builds fall back to the debug signing key — fine for a private test
link, **not** acceptable for Play.

## 5. Build the release (me, once the API URL exists)

```bash
cd mobile
flutter build apk --release --dart-define=API_BASE_URL=https://careeros-api.onrender.com/api/v1 --dart-define=ENVIRONMENT=production
flutter build appbundle --release --dart-define=API_BASE_URL=https://careeros-api.onrender.com/api/v1 --dart-define=ENVIRONMENT=production
```

- `app-release.apk` → the direct download link (~70 MB: it carries every CPU architecture; add
  `--split-per-abi` for ~25 MB per-architecture APKs if download size matters).
- `app-release.aab` → what Play Console accepts (Play splits it per device automatically).

`tool/build_release.sh` wraps both with the URL as its only argument.

## 6. Host the APK (direct download track)

GitHub Releases is the simplest host that gives a stable link:

1. GitHub → the repo → **Releases** → **Draft a new release** → tag `v0.1.0`.
2. Attach `app-release.apk`, publish, share the asset URL.

Android shows a "unknown sources" warning for any APK installed outside Play — expected; the user
allows installs from the browser once. If the repo is private, download links require a login, so
either make the repo public or use another file host.

## 7. Play Store track

You need: a Play Console account ($25 one-off, your card), and a publicly reachable privacy policy
URL. Everything else I prepare: listing text, screenshots, feature graphic, content rating answers
and the Data safety form (the app collects account, CV and application data; email tracking ships
disabled, which changes those answers — worth stating accurately).

Review is typically 1–7 days for a new developer account. Nothing about the direct APK link blocks
or delays the Play submission.

## Known gaps to accept or fix before real users

- **iOS is unverified** — no Mac in this project, so this launch is Android-only.
- **Gmail/Outlook tracking ships off** — they need their own OAuth apps plus Google's
  restricted-scope verification.
- **Single instance only** — the scheduler's multi-instance leader election is not implemented, so
  keep `careeros-api` at one instance (see SYSTEM_AUDIT.md §35).
- **Free-tier sleep** — a sleeping API makes the app's first request slow; a paid instance removes it.
