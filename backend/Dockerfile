# Production image (Phase 11, spec §14-15). Never runs `uvicorn --reload` — gunicorn manages a
# pool of uvicorn worker processes with real graceful-shutdown/timeout behavior.
#
# This backend serves both the API and the in-process APScheduler (see app/scheduler.py) — there
# is no separate "worker" container in this architecture, because there is no external task queue
# (Redis/Celery) deployed; `app/services/background_tasks.py`'s `InlineTaskRunner` processes
# webhook-triggered work inline. Running more than one replica of this image is safe: the
# scheduler's jobs are protected by a Postgres advisory-lock leader-election check (spec §22, see
# app/scheduler.py's `_acquire_leader_lock`) so only one replica's timer actually executes each
# job tick. See DEPLOYMENT.md for the honest account of why this differs from a literal
# api/worker/scheduler three-container split, and what would need to change to introduce one
# (a real queue, and moving webhook processing off the request path).
FROM python:3.12-slim AS base

# Runs as a non-root user — a container escaping to root is a materially worse outcome than one
# confined to an unprivileged account.
RUN useradd --create-home --shell /bin/bash careeros
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R careeros:careeros /app
USER careeros

EXPOSE 8000

# Worker count/timeouts are environment-configurable (spec §15) via gunicorn's own env vars
# (GUNICORN_CMD_ARGS) or by overriding this CMD in your orchestrator — 4 workers and a 60s timeout
# are reasonable single-instance defaults, not a hardcoded ceiling.
CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "60", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]
