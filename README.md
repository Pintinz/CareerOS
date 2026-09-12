# CareerOS

**Your Career Intelligence & Opportunity Platform**
_Skills Today. Opportunities Tomorrow. A Brighter You._

CareerOS is a career platform combining job/scholarship/internship discovery, CV/ATS analysis,
aptitude-test and interview preparation, application tracking, and company intelligence.

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for what is actually built vs. planned, and
[`ARCHITECTURE.md`](ARCHITECTURE.md) for the system design.

## Monorepo layout

```
CareerOS/
├── mobile/     Flutter app (Android + iOS)
├── backend/    FastAPI + PostgreSQL API
├── admin/      Next.js admin portal
├── docs/       supplementary docs
└── docker-compose.yml
```

## Prerequisites

| Tool | Required for | Status on reference dev machine |
|---|---|---|
| Python 3.11+ | backend | available |
| Node.js 18+ | admin | available |
| Flutter 3.x / Dart + Android SDK + JDK 17 | mobile | installed and verified — see `DEPLOYMENT.md` → "Mobile toolchain setup" for the exact working setup (including a gotcha: use a JDK **zip**, not an installer) |
| Docker + Docker Compose | Postgres/local stack | **not installed** — install Docker Desktop to use `docker-compose.yml` |

## Quick start

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\Activate.ps1 in PowerShell
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/api/v1/health`

### Admin (Next.js)

```bash
cd admin
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000

### Mobile (Flutter)

`android/`/`ios/` platform folders are already generated and committed. Just:

```bash
cd mobile
flutter pub get
flutter run
```

To rebuild from scratch on a new machine, see `DEPLOYMENT.md` → "Mobile toolchain setup".

### Full stack via Docker (once Docker is installed)

```bash
docker compose up
```

## Development rules

This project follows the CareerOS build rules in the master spec: no fake AI claims, no fabricated
job/scholarship/news content presented as real, every feature ships with loading/empty/error/offline
states, and any feature blocked by a missing external credential gets a full provider-abstraction +
mock implementation rather than being skipped.
