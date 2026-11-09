FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install system dependencies for GeoDjango, GDAL, GEOS, PROJ, and PostGIS client
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    build-essential \
    libpq-dev \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and dynamically install GDAL matching host Debian version
COPY requirements.txt ./
RUN GDAL_VERSION=$(gdal-config --version) && \
    pip install --no-cache-dir "GDAL==${GDAL_VERSION}.*" && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY . /app/

# Ensure directories exist and entrypoint has executable rights and LF line endings
RUN mkdir -p /app/media /app/staticfiles /app/media/fixtures && \
    dos2unix /app/scripts/start.sh && \
    chmod +x /app/scripts/start.sh

EXPOSE 8000

CMD ["/bin/bash", "/app/scripts/start.sh"]
