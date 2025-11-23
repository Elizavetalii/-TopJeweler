#!/usr/bin/env bash
set -euo pipefail

# Working dir: /srv/app/lumieresecrete (set in Dockerfile)

echo "[entrypoint] Waiting for the database to be ready..."
python - <<'PY'
import os, time
import psycopg2

DB_NAME = os.getenv('DJANGO_DB_NAME', 'lumieresecrete_db')
DB_USER = os.getenv('DJANGO_DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DJANGO_DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DJANGO_DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DJANGO_DB_PORT', '5432'))

for i in range(60):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        conn.close()
        print('[entrypoint] Database is ready')
        break
    except Exception as e:
        print(f"[entrypoint] DB not ready yet ({e}); retry {i+1}/60...")
        time.sleep(1)
else:
    raise SystemExit('[entrypoint] Database not ready after 60s, exiting')
PY

echo "[entrypoint] Running migrations..."
python manage.py migrate --noinput

if [[ "${DJANGO_DEBUG:-True}" == "False" ]]; then
  echo "[entrypoint] Collecting static files..."
  python manage.py collectstatic --noinput || true
else
  echo "[entrypoint] DEBUG=True -> skip collectstatic"
fi

if [[ -n "${INITIAL_FIXTURE:-}" ]]; then
  echo "[entrypoint] Loading initial fixture from ${INITIAL_FIXTURE}..."
  if [[ -f "${INITIAL_FIXTURE}" ]]; then
    python manage.py loaddata "${INITIAL_FIXTURE}" || echo "[entrypoint] loaddata failed (continuing)"
  else
    echo "[entrypoint] Fixture file not found: ${INITIAL_FIXTURE} (skipping)"
  fi
fi

echo "[entrypoint] Starting app: $*"
exec "$@"
