FROM python:3.12-slim

# System dependencies for GeoDjango/GDAL/GEOS/PROJ + build tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils libproj-dev gdal-bin libgdal-dev \
    libgeos-dev build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/staticfiles

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
