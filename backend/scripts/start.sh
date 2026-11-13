
#!/usr/bin/env bash

set -Eeuo pipefail

echo "=========================================================="
echo " Starting GeoHarmonize Backend"
echo " Environment: ${RENDER:-Local}"
echo " Port: ${PORT:-8000}"
echo "=========================================================="

cd /app

# 1. Initialize and verify PostGIS
echo "[1/5] Checking PostGIS..."

python scripts/init_postgis.py

# 2. Apply database migrations
echo "[2/5] Applying database migrations..."

python manage.py migrate --noinput

# 3. Collect static files
echo "[3/5] Collecting static files..."

python manage.py collectstatic --noinput

# 4. Create administrator only when explicitly enabled
echo "[4/5] Checking administrator bootstrap configuration..."

if [[ "${BOOTSTRAP_ADMIN:-false}" =~ ^(1|true|yes|on)$ ]]; then
    python manage.py init_admin
else
    echo "Administrator bootstrap disabled. Skipping."
fi

# 5. Start Gunicorn
echo "[5/5] Starting Gunicorn..."

TARGET_PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${TARGET_PORT}" \
    --workers "${WORKERS}" \
    --timeout "${TIMEOUT}" \
    --access-logfile - \
    --error-logfile -
