
# ==========================================================
# GeoHarmonize - Production Backend Dockerfile
# Platform: Render
# Python: 3.12
# Framework: Django + GeoDjango
# Database: PostgreSQL + PostGIS
# ==========================================================

FROM python:3.12-slim

# ----------------------------------------------------------
# 1. Python environment
# ----------------------------------------------------------

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

# ----------------------------------------------------------
# 2. Install system-level geospatial dependencies
# ----------------------------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    binutils \
    curl \
    dos2unix \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------
# 3. Application directory
# ----------------------------------------------------------

WORKDIR /app

# ----------------------------------------------------------
# 4. Install Python dependencies
# Copy requirements first for Docker layer caching
# ----------------------------------------------------------

COPY backend/requirements.txt /app/requirements.txt

RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel; \
    python -m pip install -r /app/requirements.txt; \
    python -m pip check

# ----------------------------------------------------------
# 5. Copy backend application
# ----------------------------------------------------------

COPY backend/ /app/

# ----------------------------------------------------------
# 6. Prepare runtime directories and startup script
# ----------------------------------------------------------

RUN set -eux; \
    mkdir -p /app/media /app/staticfiles /app/media/fixtures; \
    dos2unix /app/scripts/start.sh; \
    chmod +x /app/scripts/start.sh

# ----------------------------------------------------------
# 7. Runtime configuration
# ----------------------------------------------------------

EXPOSE 8000

# Render dynamically assigns PORT.
# start.sh reads PORT and starts Gunicorn.

CMD ["/bin/bash", "/app/scripts/start.sh"]
