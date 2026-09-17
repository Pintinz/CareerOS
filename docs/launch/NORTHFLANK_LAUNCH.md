# Going live on Northflank (free Developer Sandbox)

The free Sandbox gives **2 always-on services + 1 database** per account — exactly CareerOS:
`careeros-api`, `careeros-admin` and a PostgreSQL database. Nothing sleeps. A card is required on the
account, but every resource below uses the free allowance; Northflank marks free plans in the UI —
if a screen only offers a paid plan, stop and check before confirming.

Nothing in this guide needs a secret to pass through chat: you generate and paste them yourself.

| Step | Who |
|---|---|
| 1. Account (GitHub sign-in) + card | you |
| 2. Connect GitHub repo `Pintinz/CareerOS` | you |
| 3–8. Project, database, secrets, two services | you (I can guide each screen) |
| 9. Verify the API serves your content | me |
| 10. Release APK/AAB against the live URL | me |

---

## 1. Account

northflank.com → **Sign up** → **Continue with GitHub** → add a card when asked (Billing).

## 2. Connect the repository

Account settings → **Git** → **GitHub** → install the Northflank app → grant access to
**`Pintinz/CareerOS`** only.

## 3. Project

**Create project** → name `careeros` → region: the closest Europe region offered (lowest latency to
Nigeria of Northflank's managed regions).

## 4. Database

In the project: **Create new → Addon → PostgreSQL**

- Name: `careeros-db`
- Version: latest
- **TLS: on**
- Resources: the free option
- Create, and wait for status **Running**.

## 5. Generate the three secrets (on your machine)

```bash
cd backend
.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
.venv/Scripts/python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The first is `JWT_SECRET_KEY`, the second is `TOKEN_ENCRYPTION_KEYS`. Keep both in your password
manager. You also need an admin email and a strong password (12+ characters).

## 6. Secret group for the API

**Create new → Secret group** → name `careeros-api-env` → type *Runtime variables*.

Variables:

| Key | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `JWT_SECRET_KEY` | first value from step 5 |
| `TOKEN_ENCRYPTION_KEYS` | second value from step 5 |
| `ADMIN_SEED_EMAIL` | your admin email |
| `ADMIN_SEED_PASSWORD` | your admin password |
| `BOOTSTRAP_CONTENT` | `true` |
| `WEB_CONCURRENCY` | `1` |
| `GMAIL_TRACKING_ENABLED` | `false` |
| `OUTLOOK_TRACKING_ENABLED` | `false` |
| `CAREER_SOURCE_SYNC_ENABLED` | `true` |
| `SOURCE_AUTO_PUBLISH_ENABLED` | `false` |

**Linked addons** → `careeros-db` → key **`POSTGRES_URI`** → alias **`DATABASE_URL`**.
(The API accepts the addon's `postgresql://…?sslmode=…` URL as-is.)

**Restrictions** → apply only to the service `careeros-api` (created next).

`PUBLIC_BASE_URL` and `CORS_ORIGINS` are added in step 8, once the URLs exist.

## 7. API service

**Create new → Service → Combined service** (builds from Git and deploys)

- Name: `careeros-api`
- Repository: `Pintinz/CareerOS`, branch `main`
- Build type: **Dockerfile**
  - Dockerfile location: `/backend/Dockerfile`
  - Build context: `/backend`
- Networking → port **8000**, protocol **HTTP**, **Publicly expose** on
- Health check (optional but recommended): HTTP, port 8000, path `/api/v1/liveness`
- Resources: the free option · Instances: 1
- Create.

The first build takes several minutes. On start the image runs database migrations, then imports
your content pack (85 companies, 192 published opportunities, question banks). The logs show
`content bootstrap complete` when it's done.

Copy the public URL from the service's **Ports** panel — it looks like
`https://p01--careeros-api--<id>.code.run`.

## 8. Admin service

**Create new → Service → Combined service**

- Name: `careeros-admin`
- Repository: `Pintinz/CareerOS`, branch `main`
- Build type: **Dockerfile**
  - Dockerfile location: `/admin/Dockerfile`
  - Build context: `/admin`
- **Build arguments:** `NEXT_PUBLIC_API_BASE_URL` = `<API URL from step 7>/api/v1`
- Networking → port **3000**, HTTP, publicly exposed
- Resources: the free option
- Create, then copy its public URL.

Back in the secret group `careeros-api-env`, add:

| Key | Value |
|---|---|
| `PUBLIC_BASE_URL` | the API URL (no trailing slash) |
| `CORS_ORIGINS` | the admin URL (no trailing slash) |

Then **restart** `careeros-api` so it picks them up.

## 9. Verify

- `<API URL>/api/v1/liveness` → `{"status": "alive"}`
- `<API URL>/api/v1/jobs?page_size=1` → `total` around 192
- Admin URL → log in with the seed admin → **change the password**, then delete
  `ADMIN_SEED_PASSWORD` from the secret group.

## 10. Release build

Send me the API URL; I build `app-release.apk` and `.aab` against it with
`mobile/tool/build_release.sh <API URL>/api/v1`.

---

## Things to know

- **Sandbox is for launch and early users.** Northflank describes it as not for production; when
  traffic grows, move the services to a paid plan in place — no code change.
- **Uploaded images are not persistent.** The bundled content pack restores its logos and question
  images on every start. Images uploaded later through the live admin need persistent storage
  (a Northflank volume or Cloudflare R2) before you rely on them.
- **Keep `BOOTSTRAP_CONTENT=true` until you publish directly in the live admin.** After that set it
  to `false` so a restart can't overwrite newer live edits with the snapshot.
- **Out of memory?** If a service restarts with OOM on the smallest free size, tell me — the API can
  drop background discovery to lower memory, or the admin can move to a static host.
