# 🚀 Deploying GeoHarmonize to Render

This guide explains how to deploy the **GeoHarmonize Backend** and **Frontend** to [Render](https://render.com) with full **PostgreSQL + PostGIS + GDAL** support.

---

## 🔍 Why Backend Deployment Failed Previously on Render

If your previous deployment on Render failed, here is why:
1. **Render Native Python Environment Has No GDAL**: Render's default native Python runtime runs on standard Ubuntu without the OS-level GDAL, GEOS, and PROJ C-libraries (`libgdal-dev`, `gdal-bin`, `libgeos-dev`). `pip install -r requirements.txt` failed because `GDAL` and geospatial packages require pre-compiled C-extensions.
2. **Missing Root Dockerfile**: Render looks for `Dockerfile` in the root directory by default. The repository only had `backend/Dockerfile`, causing "Dockerfile not found".
3. **Hardcoded Port 8000**: Render assigns a dynamic port via the `$PORT` environment variable (typically 10000). Gunicorn was hardcoded to `0.0.0.0:8000`, causing Render's health checks to time out.
4. **`DATABASE_URL` Not Read**: Render passes database credentials as a single `DATABASE_URL` connection string. The backend previously only read `POSTGRES_HOST=db`, causing it to fail to connect to the cloud database.
5. **Debian GDAL Version Mismatch**: Debian 12 Bookworm bundles GDAL 3.6.x, while `requirements.txt` hardcoded `GDAL==3.8.4`, causing pip compile failure.
6. **No Automated Startup Lifecycle**: The container started without running database migrations (`migrate`), static file collection (`collectstatic`), or admin initialization (`init_admin`).

---

## ✅ What Was Fixed

1. **Dockerized Environment with C-GDAL**: Added a root `Dockerfile` and updated `backend/Dockerfile` with Debian Bookworm, installing `gdal-bin`, `libgdal-dev`, `libgeos-dev`, and dynamically matching the Python `GDAL` bindings.
2. **Dynamic Port Binding**: Startup script now binds to `0.0.0.0:${PORT:-8000}`, satisfying Render's port scanner.
3. **`DATABASE_URL` Support with `dj-database-url`**: Django now parses Render's connection string, sets the PostGIS spatial engine, and handles SSL.
4. **Automated Startup Script (`backend/scripts/start.sh`)**:
   - Automatically runs `CREATE EXTENSION IF NOT EXISTS postgis;`
   - Runs `python manage.py migrate --noinput`
   - Runs `python manage.py collectstatic --noinput`
   - Supports opt-in administrator bootstrap via environment variables:
     - `BOOTSTRAP_ADMIN=true`
     - `ADMIN_USERNAME=<your-chosen-username>`
     - `ADMIN_EMAIL=<your-email>`
     - `ADMIN_PASSWORD=<your-secure-password-min-12-chars>`
5. **Render Blueprint (`render.yaml`)**: Complete Infrastructure-as-Code for 1-click provisioning of the PostGIS database, Docker backend, and static frontend.
6. **Cloud Host Headers & CORS**: `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` now automatically detect `.onrender.com` and `RENDER_EXTERNAL_HOSTNAME`.

---

## 🛠️ Method 1: 1-Click Deployment Using Render Blueprint (Recommended)

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Configure Render PostGIS deployment and UI enhancements"
   git push origin main
   ```
2. Go to your [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** (top right) -> Select **Blueprint**.
4. Connect your GitHub repository (`sarveshsuyal/Geoharmonize-main`).
5. Render will automatically read `render.yaml` and display:
   - `geoharmonize-postgis-db` (PostgreSQL Database)
   - `geoharmonize-backend` (Web Service via Docker)
   - `geoharmonize-frontend` (Static Site via React + Vite)
6. Click **Apply**.
7. Wait 3–5 minutes for the build to finish. Once done, your backend and frontend will be live with public HTTPS URLs!

---

## 🛠️ Method 2: Manual Web Service Setup on Render

If you prefer to configure the service manually on the Render dashboard:

### Step 1: Create the PostgreSQL Database
1. In Render Dashboard, click **New +** -> **PostgreSQL**.
2. Name: `geoharmonize-db`
3. Database: `geoharmonize`
4. User: `geoharmonize`
5. Plan: **Free**
6. Click **Create Database**.
7. Once created, copy the **Internal Database URL** (or External URL).

### Step 2: Create the Backend Web Service
1. Click **New +** -> **Web Service**.
2. Select **Build and deploy from a Git repository**.
3. Connect `sarveshsuyal/Geoharmonize-main`.
4. Fill in the service details:
   - **Name**: `geoharmonize-backend`
   - **Region**: Same region as your database (e.g. Oregon)
   - **Branch**: `main`
   - **Runtime**: **Docker** ⚠️ *(Do NOT select Python! Must select Docker)*
   - **Dockerfile Path**: `./Dockerfile` (or `./backend/Dockerfile` with Docker Context `./backend`)
   - **Plan**: **Free**
5. Under **Advanced** -> **Add Environment Variables**:
   - `DATABASE_URL`: *(Paste your Render database connection string)*
   - `DJANGO_SECRET_KEY`: `generate-a-strong-random-key`
   - `DJANGO_DEBUG`: `False`
   - `DJANGO_ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`
   - `CORS_ALLOW_ALL_ORIGINS`: `True`
   - `PROJECT_TARGET_CRS`: `EPSG:32644`
6. Click **Create Web Service**.

---

## 🌐 Verifying Your Deployment

1. **Health Check Endpoint**:
   Open in your browser:
   `https://<your-backend-name>.onrender.com/health/`
   You should see:
   ```json
   {
     "status": "ok",
     "service": "geoharmonize-api",
     "version": "1.0.0",
     "platform": "Render / Docker Cloud",
     "database": {
       "connected": true,
       "postgis_ready": true,
       "postgis_version": "3.4.x ..."
     }
   }
   ```
2. **Admin Portal**:
   Visit `https://<your-backend-name>.onrender.com/admin/`
   Log in with your configured administrator credentials (set via `ADMIN_USERNAME` and `ADMIN_PASSWORD` or created via `manage.py createsuperuser`).

---

## 💡 Note on Render Free Tier "Cold Starts"

On Render's Free tier, web services spin down after 15 minutes of inactivity. When a new request arrives, Render will take **30 to 50 seconds** to wake up the container. 

The GeoHarmonize frontend includes an automatic **live backend status detector** and **cold-start countdown** on the login screen to keep users informed while Render spins up!
