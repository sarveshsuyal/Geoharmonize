# GeoHarmonize
**Multi-Source Geospatial Land Record Harmonization Platform**  
*Prototype for SIH26013 — Department of Land Resources, Ministry of Rural Development, Government of India.*

[![Target Repository](https://img.shields.io/badge/GitHub-sarveshsuyal%2FGeoharmonize-blue?logo=github)](https://github.com/sarveshsuyal/Geoharmonize)
[![Backend Runtime](https://img.shields.io/badge/Backend-Django%205%20%7C%20GeoDjango-green?logo=django)](https://www.djangoproject.com/)
[![Frontend Runtime](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%205-purple?logo=vite)](https://vitejs.dev/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016%20%2B%20PostGIS-336791?logo=postgresql)](https://postgis.net/)

---

## A. Project Overview

Different government and geospatial authorities (cadastral revenue maps, drone surveys, municipal GIS, GNSS field records, and satellite imagery) frequently represent the same physical land parcels with conflicting coordinate systems, shifted boundaries, divergent attribute naming, and varying spatial resolutions.

**GeoHarmonize** ingests, validates, aligns, and harmonizes multi-source land records into an authoritative, topologically consistent spatial dataset with full audit provenance.

### Core Capabilities
1. **Multi-Source Ingestion:** Ingests GeoJSON, Shapefile ZIPs, GeoTIFF rasters, KML/KMZ, CSV coordinates, and satellite imagery.
2. **CRS Normalization:** Automatically inspects dataset coordinate reference systems (never assumes) and re-projects vectors and rasters to the designated project target CRS (`EPSG:32644` by default).
3. **Automated Feature Extraction:** Employs an OpenCV-based computer-vision pipeline (Canny edge detection, morphological closing, contour analysis, and solidity scoring) to extract building footprint candidates and parcel boundaries from imagery without fabricating unverified ML claims.
4. **Multi-Factor Parcel Matching:** Computes quantitative geometric similarity scores (Intersection-over-Union, area discrepancy, centroid distance decay, and compactness similarity).
5. **Canonical Attribute Mapping:** Normalizes disparate revenue aliases (`survey_no`, `khasra_no`, `SurveyNumber` → `survey_number`).
6. **Topology Validation & Safe Repair:** Detects slivers, self-intersections, duplicates, and overlaps, recording full before/after geometry audit trails in `TopologyEdit`.
7. **Conflict Detection & Human Review:** Flags boundary discrepancies, overlapping claims, and utility/building encroachments, routing borderline matches (confidence 55–80%) to GIS Officers for human review (*Accept*, *Keep Existing*, *Edit Geometry*, *Reject*, *Field Verification*).
8. **Multi-Temporal Change Detection:** Compares multi-year cadastral datasets to categorize changes as `ADDED`, `REMOVED`, `MODIFIED`, or `UNCHANGED`.
9. **Decision-Support Reporting:** Exports conflict logs and harmonization summaries in CSV and PDF formats.

> [!IMPORTANT]
> **Advisory Disclaimer:** GeoHarmonize is explicitly an analytical decision-support and data-harmonization platform. It does not decide or confer legal land ownership. Legal ownership remains an authoritative attribute derived from statutory revenue records.

---

## B. Architecture and Technology Stack

```
                       ┌────────────────────────────┐
                       │        Client Browser      │
                       └──────────────┬─────────────┘
                                      │  HTTPS / JWT
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │       Frontend: React 18 + Vite 5 SPA           │
             │  • Tailwind CSS 3.4  • Leaflet & React-Leaflet  │
             │  • Hosted on Vercel (rewrites via vercel.json)   │
             └────────────────────────┬────────────────────────┘
                                      │  REST API (CORS + Bearer JWT)
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │     Backend: Django 5.0 + GeoDjango REST API    │
             │  • Gunicorn WSGI Server (Docker on Render)      │
             │  • djangorestframework-gis & SimpleJWT auth     │
             │  • GDAL, GEOS, PROJ, Fiona, Rasterio, Shapely   │
             │  • Computer Vision: OpenCV (Headless) + NumPy   │
             └────────────────────────┬────────────────────────┘
                                      │  SQL / Spatial Queries
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │         Database: PostgreSQL 16 + PostGIS       │
             │  • Spatial geometry storage & GiST spatial index│
             │  • Managed cloud database (Render / AWS RDS)    │
             └─────────────────────────────────────────────────┘
```

### Directory Structure
```
Geoharmonize/
├── Dockerfile                  # Production multi-stage Docker build with system GDAL/GEOS
├── docker-compose.yml          # Local multi-container development configuration
├── render.yaml                 # Render Infrastructure-as-Code blueprint
├── .dockerignore               # Docker context exclusion rules
├── .gitattributes              # Line-ending normalizer (enforces LF on shell scripts)
├── README.md                   # Complete developer & deployment guide
├── DEPLOY_RENDER.md            # Render deployment checklist
├── algo_selftest/              # Standalone algorithm verification scripts
│   ├── test_matching_confidence.py
│   ├── test_cv_pipeline.py
│   └── test_ai_analysis_pipeline.py
├── backend/
│   ├── manage.py
│   ├── requirements.txt        # Production Python dependencies
│   ├── .env.example            # Environment template with safe placeholders
│   ├── config/                 # Django settings, root URLs, WSGI/ASGI entrypoints
│   ├── scripts/
│   │   ├── init_postgis.py     # Database extension initializer and verification
│   │   └── start.sh            # Production container startup lifecycle
│   └── apps/
│       ├── accounts/           # User model, Role RBAC (ADMIN, GIS_OFFICER, REVIEWER, VIEWER)
│       ├── datasets/           # Dataset ingestion, CRS detection, vector/raster IO
│       ├── geospatial/         # Topology validation, geometry repair, bbox GeoJSON
│       ├── parcels/            # Canonical Parcel, Building, Road, Utility models
│       ├── harmonization/      # Matching engine, confidence scoring, field mapping
│       ├── conflicts/          # Conflict detection engine & review action audit logs
│       ├── ai/                 # OpenCV feature extraction, raster tiling, recommendations
│       ├── change_detection/   # Multi-temporal parcel comparison
│       ├── dashboard/          # Real-time statistics aggregation API
│       └── reports/            # CSV and ReportLab PDF report generation
└── frontend/
    ├── package.json            # Vite, React 18, Leaflet, Tailwind dependencies
    ├── vite.config.js          # Vite configuration
    ├── vercel.json             # Vercel SPA client-side route rewrites
    ├── .env.example            # Frontend environment template
    └── src/
        ├── App.jsx             # React Router routing configuration
        ├── pages/              # 10 dedicated view pages (Dashboard, Map, Review, etc.)
        ├── map/                # Leaflet controls, basemaps, AI overlay tools
        ├── layouts/            # Dashboard sidebar and responsive navigation layout
        └── services/           # Axios HTTP client, JWT interceptor, AuthContext
```

---

## C. Prerequisites

- **Python:** 3.12 (standard for the containerized backend).
- **Node.js:** Node.js 18.x, 20.x, or 24.x and npm 10+.
- **Docker:** Docker Desktop or Docker Engine with Docker Compose (recommended for local development to bundle GDAL and PostgreSQL/PostGIS).
- **Native Geospatial Libraries (if running without Docker):**
  - GDAL (`libgdal-dev`, `gdal-bin` >= 3.6)
  - GEOS (`libgeos-dev` >= 3.11)
  - PROJ (`libproj-dev` >= 9.0)
  - PostgreSQL client library (`libpq-dev`)

---

## D. Local Setup

### Option 1: Running with Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sarveshsuyal/Geoharmonize.git
   cd Geoharmonize
   ```

2. **Set up local environment files:**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. **Start services:**
   ```bash
   docker compose up --build
   ```

4. **Apply database migrations and create an administrator (in a separate terminal):**
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py createsuperuser
   ```

---

### Option 2: Running Native (Without Docker)

#### 1. Backend Setup
```bash
# Install Ubuntu/Debian system libraries:
sudo apt-get update && sudo apt-get install -y \
    binutils libproj-dev gdal-bin libgdal-dev libgeos-dev libpq-dev

# Create and activate Python virtual environment:
cd backend
python3.12 -m venv venv
source venv/bin/activate    # On Windows: .\venv\Scripts\Activate.ps1

# Install Python dependencies:
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment:
cp .env.example .env
# Edit .env with your local PostgreSQL credentials

# Run database migrations:
python manage.py migrate

# Create initial administrator:
python manage.py createsuperuser

# Start Django development server:
python manage.py runserver 0.0.0.0:8000
```

#### 2. Frontend Setup
```bash
cd ../frontend
npm install
cp .env.example .env

# Start Vite development server:
npm run dev
```

### Verified Local Endpoints
- **Frontend App:** `http://localhost:5173`
- **Backend API Root:** `http://localhost:8000/api/`
- **Health Check Endpoint:** `http://localhost:8000/health/`
- **Django Admin Portal:** `http://localhost:8000/admin/`

---

## E. Environment Variables

### Backend Configuration (`backend/.env` & Cloud Environment)

| Variable Name | Required | Default / Example | Purpose / Production Location |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Yes (in Prod) | `postgresql://user:pass@host:5432/db` | Full PostgreSQL+PostGIS connection string (Render DB) |
| `DJANGO_SECRET_KEY` | Yes | `(secure-random-key)` | Cryptographic secret for signing sessions and JWT tokens |
| `DJANGO_DEBUG` | No | `False` | Must be `False` in production; enables verbose errors in dev |
| `DJANGO_ALLOWED_HOSTS` | Yes | `.onrender.com,localhost,127.0.0.1` | Hostnames allowed in HTTP Host headers |
| `FRONTEND_URL` | Yes | `https://<your-project>.vercel.app` | Primary frontend domain for CORS and CSRF allowlists |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | Comma-separated CORS allowed origins |
| `CSRF_TRUSTED_ORIGINS` | No | `http://localhost:5173` | Comma-separated trusted origins for CSRF POST validation |
| `PROJECT_TARGET_CRS` | No | `EPSG:32644` | Default spatial reference system for harmonization |
| `MAX_UPLOAD_SIZE_MB` | No | `200` | Maximum file size for multi-part dataset uploads |
| `BOOTSTRAP_ADMIN` | No | `False` | Opt-in flag to create initial admin user on container start |
| `ADMIN_USERNAME` | Conditional | `admin` | Initial admin username (used only if `BOOTSTRAP_ADMIN=true`) |
| `ADMIN_EMAIL` | Conditional | `admin@example.com` | Initial admin email (used only if `BOOTSTRAP_ADMIN=true`) |
| `ADMIN_PASSWORD` | Conditional | `(min-12-chars)` | Initial admin password (used only if `BOOTSTRAP_ADMIN=true`) |

### Frontend Configuration (`frontend/.env` & Vercel Dashboard)

| Variable Name | Required | Default / Example | Purpose |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Yes | `https://<backend-app>.onrender.com/api` | API root path consumed by Axios client |
| `VITE_MAPTILER_API_KEY` | No | `(empty)` | Optional API key for MapTiler satellite basemaps |

---

## F. Deployment: Preferred Vercel + Render Architecture

GeoHarmonize uses a split architecture: **Vercel** hosts the static React SPA frontend, and **Render** hosts the containerized GeoDjango backend and managed PostgreSQL/PostGIS database.

```
+------------------------------------+         +-------------------------------------+
|        VERCEL (Frontend SPA)       |         |       RENDER (Backend Web Service)  |
| - Root Directory: frontend         |  CORS   | - Runtime: Docker (./Dockerfile)    |
| - Framework: Vite                  | ------> | - Environment: Python 3.12 + PostGIS|
| - Build: npm run build             |  HTTPS  | - Health Check Path: /health/       |
| - Output: dist                     |         | - Auto-deploys from GitHub `main`   |
+------------------------------------+         +-------------------------------------+
                                                                  |
                                                                  v
                                               +-------------------------------------+
                                               |       RENDER (PostgreSQL + PostGIS) |
                                               | - PostgreSQL 16                     |
                                               | - PostGIS spatial extensions        |
                                               +-------------------------------------+
```

### Step 1: Push Code to GitHub
Ensure all changes are committed and pushed to `https://github.com/sarveshsuyal/Geoharmonize` on branch `main`.

### Step 2: Database Provisioning on Render
1. In the [Render Dashboard](https://dashboard.render.com/), select **New +** > **PostgreSQL**.
2. Name the database `geoharmonize-db`, user `geoharmonize`, version `16`.
3. Once provisioned, copy the **Internal Database URL** (e.g. `postgresql://geoharmonize:...@dpg-...-a/geoharmonize`).

### Step 3: Backend Deployment on Render
1. Select **New +** > **Web Service** and connect `sarveshsuyal/Geoharmonize`.
2. Configure service parameters:
   - **Runtime:** `Docker` *(Do NOT select Native Python; Docker is required for C-GDAL libraries)*.
   - **Dockerfile Path:** `./Dockerfile`
   - **Docker Context:** `.`
   - **Health Check Path:** `/health/`
3. Add Environment Variables:
   - `DATABASE_URL`: `[Paste Internal Database URL from Step 2]`
   - `DJANGO_SECRET_KEY`: `[Generate a secure random string]`
   - `DJANGO_DEBUG`: `False`
   - `DJANGO_ALLOWED_HOSTS`: `.onrender.com`
   - `FRONTEND_URL`: `https://<your-vercel-domain>.vercel.app`
   - `CORS_ALLOWED_ORIGINS`: `https://<your-vercel-domain>.vercel.app`
   - `CSRF_TRUSTED_ORIGINS`: `https://<your-vercel-domain>.vercel.app`
4. Deploy the service. The container will automatically execute `init_postgis.py`, run `manage.py migrate`, collect static files, and launch Gunicorn on `$PORT`.

### Step 4: Frontend Deployment on Vercel
1. In the [Vercel Dashboard](https://vercel.com/), click **Add New...** > **Project** and import `sarveshsuyal/Geoharmonize`.
2. Configure build settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Under **Environment Variables**, add:
   - `VITE_API_BASE_URL` = `https://<your-render-backend-name>.onrender.com/api`
4. Click **Deploy**. Vercel will build the React SPA and provide a production HTTPS URL.

> [!NOTE]
> **Optional Render Static Frontend in `render.yaml`:**  
> The included `render.yaml` Blueprint specifies both `geoharmonize-backend` and an optional `geoharmonize-frontend`. If you deploy via Vercel, the Render static frontend is optional and does not need to be active.

---

## G. Safe Git Workflow

Always use safe Git commands to review changes before publishing:

```bash
# 1. Clone repository
git clone https://github.com/sarveshsuyal/Geoharmonize.git
cd Geoharmonize

# 2. Check current branch and uncommitted modifications
git status

# 3. Stage only specific, intended files
git add <file-name>
# Or stage all non-ignored tracked files:
git add -u

# 4. Inspect the exact staged diff before committing
git diff --cached

# 5. Commit with a descriptive message
git commit -m "feat: description of the change"

# 6. Push safely to the main branch
git push origin main
```

### Git Rules & Best Practices
- **Always inspect `git status`** before running `git add` to ensure secrets, `.env` files, or temporary artifacts are not tracked.
- **Never commit `.env` files**, private keys, or API tokens.
- **Never use `git push --force`** on shared branches.
- If GitHub reports that remote commits exist, run `git pull --rebase origin main`, inspect and resolve any conflicts locally, verify tests, and then push.

---

## H. Validation and Verification

### Commands Executed During Repository Audit
The following checks were executed by the automated audit engine:

| Check | Command Run | Result | Evidence |
| :--- | :--- | :--- | :--- |
| **Python Syntax** | `python -m compileall backend algo_selftest` | **PASS** | 50+ Python files compiled with 0 syntax errors |
| **Frontend Production Build** | `cd frontend && npm run build` | **PASS** | Vite built production bundle (`dist/`) in 8.93s |
| **Startup Script Syntax** | `bash -n backend/scripts/start.sh` | **PASS** | Shell script syntax verified with 0 errors |
| **Python 3.12 Dependencies** | `uv pip compile backend/requirements.txt` | **PASS** | All 36 dependencies resolved without conflict |
| **Dependency Consistency** | `uv pip check` | **PASS** | Verified 36 installed packages compatible |
| **Parcel Match Math Selftest** | `python algo_selftest/test_matching_confidence.py` | **PASS** | All IoU, centroid, and area assertions passed |
| **Computer Vision Selftest** | `python algo_selftest/test_cv_pipeline.py` | **PASS** | Detected 3 rectangular building footprints; rejected sliver |
| **Harmonization Unit Tests** | `apps/harmonization/tests/test_attribute_mapping.py` | **PASS** | Field mapping and alias resolution passed |

### Developer Local Verification Commands
For local verification on environments with native PostgreSQL/PostGIS installed:
```bash
# Django configuration check:
python manage.py check

# Migration integrity check (dry-run):
python manage.py makemigrations --check --dry-run

# Run full backend test suite:
pytest

# Docker container build check:
docker build -t geoharmonize-backend -f Dockerfile .
```

---

## I. Known Limitations & Production Notes

1. **Render Free Tier Cold Starts:**  
   Free-tier Render Web Services spin down after 15 minutes of inactivity. When a request arrives, wake-up requires 30–50 seconds. The GeoHarmonize login page includes an automated live backend status indicator and cold-start alert.
2. **PostGIS Support on Cloud Providers:**  
   PostGIS extensions must be enabled on the PostgreSQL instance (`CREATE EXTENSION IF NOT EXISTS postgis;`). Render includes PostGIS on all managed PostgreSQL versions.
3. **Persistent Media Storage:**  
   The application stores uploaded Shapefiles and GeoTIFFs under `/app/media/`. On ephemeral containers without persistent disks, files are cleared on restart. For large production deployments, mount a persistent disk or integrate an S3-compatible object store.
4. **Machine Learning Feature Extraction:**  
   `MLFeatureExtractor` is an intentional stub for future deep learning segmentation models. The active feature extraction pipeline uses classical computer vision (`OpenCVFeatureExtractor`).

---

## J. Repository and Contributions

- **Official Repository:** [https://github.com/sarveshsuyal/Geoharmonize](https://github.com/sarveshsuyal/Geoharmonize)  
- **Issues & Contributions:** Contributions and pull requests should be submitted via GitHub against the `main` branch.
