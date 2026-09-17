#!/bin/sh
# Container entrypoint for the CareerOS API on any host (Northflank, Render, a VPS with compose).
#
#   RUN_MIGRATIONS   "true" (default) runs `alembic upgrade head` before serving, so a deploy never
#                    serves a schema older than its code. Set "false" when migrations run elsewhere
#                    (e.g. several replicas starting at once).
#   WEB_CONCURRENCY  gunicorn worker count (default 1 — fits small instances and keeps the in-process
#                    scheduler single-leader). Raise it on bigger plans.
#   PORT             listen port (default 8000); some hosts inject their own.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
fi

exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WEB_CONCURRENCY:-1}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 60 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
