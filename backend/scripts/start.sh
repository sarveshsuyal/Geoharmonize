
#!/usr/bin/env bash
set -Eeuo pipefail

echo "=========================================="
echo " Starting GeoHarmonize Backend"
echo " Environment: ${RENDER:-Local}"
echo " Port: ${PORT:-8000}"
echo "=========================================="

cd /app

# 1. Initialize PostGIS
echo "[1/4] Checking PostGIS..."
python scripts/init_postgis.py

# 2. Apply database migrations
echo "[2/4] Applying database migrations..."
python manage.py migrate --noinput

# 3. Collect static assets
echo "[3/4] Collecting static assets..."
python manage.py collectstatic --noinput

# 4. Start Gunicorn
echo "[4/4] Starting application..."

TARGET_PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${TARGET_PORT}" \
    --workers "${WORKERS}" \
    --timeout "${TIMEOUT}" \
    --access-logfile - \
    --error-logfile -
