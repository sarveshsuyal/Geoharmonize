#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting GeoHarmonize Platform Backend"
echo " Environment: ${RENDER:+Render Cloud}${RENDER:-Standard Container}"
echo " Port: ${PORT:-8000}"
echo "=========================================================="

# 1. Ensure PostGIS extension in PostgreSQL
python scripts/init_postgis.py || true

# 2. Run database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# 3. Collect static files for WhiteNoise
echo "Collecting static assets..."
python manage.py collectstatic --noinput || true

# 4. Provision default administrator account
echo "Ensuring administrator account..."
python manage.py init_admin || true

# 5. Bind Gunicorn to the dynamic PORT assigned by Render or fallback to 8000
TARGET_PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-2}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "Launching Gunicorn on 0.0.0.0:${TARGET_PORT} with ${WORKERS} workers..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${TARGET_PORT}" \
    --workers "${WORKERS}" \
    --timeout "${TIMEOUT}" \
    --access-logfile - \
    --error-logfile -
