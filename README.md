# GeoHarmonize
**AI-Powered Multi-Source Geospatial Land Record Harmonization Platform**
Prototype for SIH26013 — Department of Land Resources, Ministry of Rural Development, Government of India.

---

## ⚠️ Important note on how this was built

This codebase was written in a sandboxed environment **with no internet access and no
Django/PostGIS/GDAL/Docker installed**, so it could not be executed or migrated end-to-end
there. What was verified in that sandbox:

- All 114+ backend Python files pass `python -m py_compile` (no syntax errors).
- The core **parcel-matching and confidence-scoring math** (IoU, area similarity,
  centroid-distance decay, shape/compactness similarity, weighted confidence)
  was re-implemented against a dependency-free mock geometry and asserted to behave
  correctly (near-identical parcels score >90%, unrelated parcels score ~0%,
  partial overlaps score in the medium band). See `algo_selftest/`.
- The classical **computer-vision building-detection pipeline** (Canny edge
  detection → morphological closing → contour detection → solidity-based
  confidence) was run for real with OpenCV/NumPy against a synthetic test image
  and correctly identified 3 rectangular "buildings" while rejecting a thin sliver.

What was **not** run here: Django's `migrate`, the DRF endpoints, GeoDjango/PostGIS
spatial queries, `docker compose up`, or the React/Vite frontend build — because none
of Django, PostGIS, GDAL, Docker, or npm packages could be installed without internet
access. **You will need to run this in an environment with internet access** (your own
machine, a cloud VM, or the SIH evaluation server) to bring it fully online. Treat this
as a complete, carefully-written first build to run, debug, and iterate on — not as a
guaranteed zero-bug deployment.

---

## What this system actually does

Different government/geospatial sources (cadastral maps, drone imagery, municipal GIS,
revenue records, GNSS surveys, satellite imagery, building/road/utility layers)
describe the same physical land differently — different CRS, formats, resolutions,
boundaries, attribute names, and accuracy. GeoHarmonize:

1. **Ingests** multiple dataset types (GeoJSON, Shapefile ZIP, GeoTIFF, KML/KMZ, CSV, imagery)
2. **Validates** files and geometries, detecting (never assuming) CRS
3. **Normalizes** every dataset into a shared project CRS
4. **Extracts features** from imagery using a classical computer-vision pipeline
   (explicitly *not* claimed to be a trained ML model — see `apps/ai/services/feature_extractor.py`)
5. **Matches** corresponding parcels across sources using measured IoU, area similarity,
   centroid distance, and shape similarity
6. **Harmonizes attributes** via a configurable field-mapping engine (`survey_no` /
   `khasra_no` / `SurveyNumber` → canonical `survey_number`, etc.)
7. **Validates topology** and safely auto-repairs simple geometry errors, keeping
   before/after geometry for every automatic edit
8. **Detects conflicts** (boundary discrepancies, area mismatches, attribute mismatches,
   building/utility-crosses-parcel, duplicates, missing parcels)
9. **Calculates confidence** (0–100, HIGH/MEDIUM/LOW) from real measured factors, never fabricated
10. **Routes uncertain cases to a human GIS officer/reviewer** for Accept / Keep Existing /
    Edit Geometry / Reject / Field Verification — every decision is logged
11. **Detects change** between two datasets/years (ADDED/REMOVED/MODIFIED/UNCHANGED)
12. Produces a **unified, traceable, harmonized GIS view** with full source provenance and audit trail

GeoHarmonize is explicitly a **decision-support and data-harmonization platform**. It
never claims to determine legal land ownership; AI/CV output is always a suggestion for
human review, and ownership is treated as an authoritative attribute from revenue
records — never inferred from imagery.

---

## Architecture

```
        USER
         │
         ▼
  React + Vite + Leaflet UI  (frontend/)
         │  REST + GeoJSON (bbox-filtered)
         ▼
  Django REST Framework API  (backend/apps/*/views.py)
         │
   ┌─────┼────────────┐
   ▼     ▼             ▼
GeoDjango  AI/CV    Processing Services
   │        │             │
   └────────┼─────────────┘
            ▼
  GDAL / GeoPandas / Shapely / Rasterio / PyProj / OpenCV
            │
            ▼
     PostgreSQL + PostGIS
            │
            ▼
   Harmonized, traceable GIS dataset
```

### Backend app structure
```
backend/
├── manage.py
├── config/                 # settings, urls, wsgi/asgi
├── apps/
│   ├── accounts/            # custom User model, roles (ADMIN/GIS_OFFICER/REVIEWER/VIEWER), JWT auth
│   ├── datasets/             # Dataset model, ingestion/CRS/metadata/geometry-validation services, upload API
│   ├── geospatial/           # cross-cutting TopologyEdit audit model, vector import, raster utilities, bbox GeoJSON API
│   ├── parcels/               # canonical Parcel/LandRecord/Building/Road/Utility models + GeoJSON APIs
│   ├── harmonization/         # HarmonizationRun, ParcelMatch, AttributeMappingRule + matching/confidence/pipeline services
│   ├── conflicts/              # Conflict, ReviewAction models + conflict-detection service + resolve API
│   ├── ai/                      # BaseFeatureExtractor / OpenCVFeatureExtractor (CV) / MLFeatureExtractor (stub), change detector
│   ├── change_detection/        # ChangeDetectionRun/ChangeFeature models + API
│   ├── dashboard/                # real-time stats API (nothing hard-coded)
│   └── reports/                   # CSV/PDF report generation
├── demo/demo_data_generator.py     # procedural multi-source demo dataset + one-click full pipeline run
├── requirements.txt
├── .env.example
└── Dockerfile
```

### Frontend page structure
```
frontend/src/
├── pages/       Dashboard, Datasets, Upload, Map, Harmonization, Conflicts, Review Queue,
│                Change Detection, Reports, Settings, Login
├── layouts/     AppLayout (sidebar navigation)
├── services/    api.js (axios client + JWT), AuthContext.jsx
└── App.jsx      routing
```

---

## Prerequisites (on the machine you actually run this on)

- Docker + Docker Compose (recommended path), **or**
- Python 3.12, GDAL/GEOS/PROJ system libraries, PostgreSQL 16 + PostGIS 3.4, Node 20+

## Running with Docker (recommended)

```bash
cp backend/.env.example backend/.env      # edit secrets as needed
cp frontend/.env.example frontend/.env
docker compose up --build
```

Then, in a second terminal:
```bash
docker compose exec backend python manage.py makemigrations accounts datasets geospatial parcels harmonization conflicts ai change_detection dashboard reports
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

- Backend API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/
- Frontend: http://localhost:5173

Log in via the frontend `/login` page (or `POST /api/auth/login/`) with the superuser
you created, assign yourself `role=GIS_OFFICER` or `ADMIN` via `/admin/`, then click
**"Run Demo"** on the Dashboard to generate a synthetic multi-source study area and
run it through the full harmonization pipeline.

## Running without Docker

```bash
# System deps (Ubuntu example):
sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev postgresql-16 postgresql-16-postgis-3

# Backend
cd backend
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set POSTGRES_HOST=localhost etc.
python manage.py makemigrations accounts datasets geospatial parcels harmonization conflicts ai change_detection dashboard reports
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Running the backend tests

```bash
cd backend
pip install pytest pytest-django
pytest
```

Tests cover: role permission helpers, login, file-extension/size validation,
CRS-missing → manual-CRS flow, geometry validation (self-intersection repair,
duplicate/overlap detection), the parcel-matching scoring formulas, the
confidence-classification thresholds, attribute-mapping, and conflict-severity
banding. See `apps/*/tests/`.

For a dependency-free sanity check of the core algorithms (no Django/GDAL needed):
```bash
python3 algo_selftest/test_matching_confidence.py
python3 algo_selftest/test_cv_pipeline.py   # requires opencv-python, numpy
```

---

## Key API endpoints

```
POST /api/auth/login/                          Login (returns JWT)
GET  /api/auth/me/                              Current user

POST /api/datasets/                             Upload dataset (multipart)
GET  /api/datasets/                              List datasets
POST /api/datasets/{id}/validate/                Re-run validation
POST /api/datasets/{id}/set-crs/                 Manually specify CRS
POST /api/datasets/{id}/process/                 Import features / run CV pipeline

POST /api/harmonization/run/                     Start harmonization run
GET  /api/harmonization/runs/{id}/               Poll run status/progress
GET  /api/harmonization/matches/                 Parcel matches

GET  /api/parcels/geojson/?bbox=minx,miny,maxx,maxy   Map-bounds-filtered parcels
GET  /api/parcels/{id}/                          Parcel detail (provenance, land record, conflicts)

GET  /api/conflicts/                             Review queue (filter by type/severity/status)
POST /api/conflicts/{id}/resolve/                Accept / Keep Existing / Edit Geometry / Reject / Field Verification

POST /api/change-detection/run/                  Compare two datasets/years
GET  /api/dashboard/stats/                       Real-time dashboard statistics
GET  /api/reports/conflicts/                     CSV report
POST /api/demo/run/                              One-click demo: generate + ingest + harmonize
```

---

## 🚀 Production Deployment Guide

### Architecture Overview
Due to system-level dependencies (**GDAL, GEOS, PROJ, PostGIS, Rasterio, OpenCV**), GeoHarmonize uses a split-tier production deployment:

```
[ USER / BROWSER ]
       │
       ▼
[ VERCEL (Static SPA) ]
  • React + Vite + Leaflet
  • Built with `npm run build`
  • SPA route rewrites via `vercel.json`
       │  API Requests (Bearer JWT + CORS)
       ▼
[ PRODUCTION BACKEND (Docker / Cloud Host / VPS) ]
  • Django 5 + Django REST Framework + GeoDjango
  • Gunicorn WSGI Server (`config.wsgi:application`)
  • System libraries: libgdal-dev, libgeos-dev, libproj-dev
       │
       ▼
[ POSTGRESQL 16 + POSTGIS 3.4 DATABASE ]
  • Spatial indexing and topology calculations
```

---

### Part 1: Frontend Deployment to Vercel

The React frontend is 100% Vercel-ready with client-side SPA routing (`vercel.json` handles `/dashboard`, `/datasets`, `/map`, `/reports`, etc. on reload).

#### Step-by-Step Vercel Deployment:
1. **Push your repository to GitHub** (see Git commands below).
2. Go to [vercel.com](https://vercel.com) and log in.
3. Click **"Add New..." → "Project"** and import your GitHub repository.
4. In the project configuration screen:
   - **Framework Preset**: `Vite` (auto-detected).
   - **Root Directory**: Click "Edit" and select `frontend` (or `geoharmonize/frontend` if the repository root is the parent folder).
   - **Build Command**: `npm run build` (default).
   - **Output Directory**: `dist` (default).
5. Expand **"Environment Variables"** and configure:
   - `VITE_API_BASE_URL` = `https://your-deployed-backend-domain.com/api`
   *(For development/testing before backend deployment, you can temporarily test against your local or staging server).*
6. Click **"Deploy"**. Vercel will build the frontend and provide a production URL (e.g. `https://geoharmonize.vercel.app`).

---

### Part 2: Backend Deployment (Why Not Vercel & Where to Deploy)

> **⚠️ Why Backend Cannot Run on Vercel**:
> Vercel Serverless and Edge Functions run ephemeral, stripped Linux micro-containers with strict package size and runtime limitations. GeoDjango requires native C/C++ shared libraries (`gdal`, `geos_c`, `proj`) and continuous connection to a PostGIS spatial database. These cannot run within Vercel's static/serverless model.

#### Recommended Backend Hosts:
1. **Render.com / Railway / Fly.io** (Using Docker):
   - The repository includes a production-ready `backend/Dockerfile` based on `python:3.12-slim` that compiles GDAL, GEOS, PROJ, and PostGIS client libraries.
   - Point your cloud provider to `backend/Dockerfile` as the build context.
   - Provision a managed PostgreSQL with PostGIS enabled (available on Render, Railway, Neon, AWS RDS, Supabase).
2. **Ubuntu Cloud VM (AWS EC2 / DigitalOcean / Hetzner)**:
   - Run the provided `docker-compose.yml`:
     ```bash
     cp backend/.env.example backend/.env
     # Configure POSTGRES_PASSWORD, DJANGO_SECRET_KEY, CORS_ALLOWED_ORIGINS in backend/.env
     docker compose up -d --build
     ```
   - Run initial migrations and create an admin user:
     ```bash
     docker compose exec backend python manage.py migrate
     docker compose exec backend python manage.py createsuperuser
     ```

#### Backend Health Check:
The backend exposes a lightweight health check endpoint at `/api/health/` (and `/health/`) returning:
```json
{"status": "ok", "service": "geoharmonize-api", "version": "0.1.0"}
```
Use this for cloud provider liveness probes.

---

### Part 3: Environment Variables Reference

#### Frontend (`frontend/.env`)
| Variable | Description | Example (Production) |
|---|---|---|
| `VITE_API_BASE_URL` | Base URL for backend DRF API | `https://api.geoharmonize.gov.in/api` |
| `VITE_MAPTILER_API_KEY` | Optional MapTiler key (default uses free Esri/OSM) | *(optional)* |

#### Backend (`backend/.env`)
| Variable | Description | Example (Production) |
|---|---|---|
| `DJANGO_SECRET_KEY` | Cryptographic secret for Django & JWT | *(random 50+ char string)* |
| `DJANGO_DEBUG` | Enable debug mode (`False` in production) | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hostnames | `api.geoharmonize.gov.in,localhost` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed frontend origins | `https://geoharmonize.vercel.app` |
| `CORS_ALLOW_VERCEL_PREVIEWS` | Allow `*.vercel.app` preview branches | `True` |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF protection | `https://geoharmonize.vercel.app` |
| `POSTGRES_DB` | PostgreSQL database name | `geoharmonize` |
| `POSTGRES_USER` | PostgreSQL user | `geoharmonize` |
| `POSTGRES_PASSWORD` | PostgreSQL password | *(strong password)* |
| `POSTGRES_HOST` | Database host (`db` in docker-compose) | `db` or `aws-rds-endpoint` |
| `POSTGRES_PORT` | Database port | `5432` |

---

### Part 4: Git Commands to Commit & Push to GitHub

To commit this project cleanly to GitHub without leaking `.env` files or temporary caches:

```bash
# 1. Stage all tracked and clean new files (ignored files are automatically skipped)
git add .

# 2. Check that no .env, node_modules, or log files are staged
git status

# 3. Create your initial deployment commit
git commit -m "feat: prepare GeoHarmonize for Vercel frontend and containerized backend deployment"

# 4. Link your remote GitHub repository and push
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

---

## Known gaps / next steps (honest MVP status)

- **Migrations are not included** in this delivery (they're generated, not hand-written,
  and require a live Django+PostGIS environment to produce correctly) — run
  `makemigrations` as shown above on first setup.
- **Celery/Redis** are wired into `docker-compose.yml` and `requirements.txt` but the
  harmonization pipeline still runs synchronously; `pipeline_service.py` documents
  exactly how to convert each step into a Celery task without restructuring.
- **PDF reports** depend on `reportlab`; CSV is the primary, always-available format.
- **MLFeatureExtractor** is an intentional stub — no trained segmentation model is
  bundled; only the classical OpenCV pipeline is implemented and clearly labeled as such.
- Frontend map performance at real government scale (thousands of parcels) would need
  server-side clustering in addition to the existing bbox filtering.
- No automated CI is configured; `pytest` and the two `algo_selftest/` scripts are the
  verification story for this submission.
