# 🚀 Deploying GeoHarmonize to Render

This guide explains how to deploy the **GeoHarmonize Backend** to [Render](https://render.com) with full **PostgreSQL + PostGIS + GDAL** support and connect it to your live **Vercel Frontend**.

- **Frontend (Vercel):** https://geoharmonize-xi.vercel.app/
- **Backend (Render):** https://geoharmonize-backend-8b1m.onrender.com
- **Target GitHub Repository:** https://github.com/sarveshsuyal/Geoharmonize

---

## 🔍 Root Cause of Render Build/Deployment Failures

If your previous Render deployment failed at ~44s, here is the exact technical diagnosis:

1. **Python 3.12 vs GDAL 3.6 Source Compilation Failure:**
   The previous `Dockerfile` attempted `pip install "GDAL==$(gdal-config --version)"`. In Debian 12 Bookworm, `gdal-config` returns version `3.6.2`. Pip attempted to compile GDAL 3.6.2 C++ bindings against Python 3.12 headers. Python 3.12 removed the legacy `longintrepr.h` header, causing `gcc` to fail immediately with a fatal compilation error at ~44s into the build.
   - **Fix Applied:** Removed `pip install GDAL==...`. GeoDjango uses `ctypes.CDLL` to link directly to `/usr/lib/libgdal.so` provided by the Debian system package `libgdal-dev` and `gdal-bin`. All other packages (`fiona`, `rasterio`, `shapely`, `geopandas`) install from modern pre-compiled manylinux wheels.
2. **Missing Database Connection Retry Loop:**
   Render Postgres databases and Web Services starting concurrently can experience brief connection refused delays before PostgreSQL is ready.
   - **Fix Applied:** `backend/scripts/init_postgis.py` now includes an automated 5-attempt retry loop and native DSN string parsing that correctly honors `sslmode=require`.
3. **Missing or Incomplete CORS / CSRF Origin Matching:**
   Django 4+ strictly enforces `CSRF_TRUSTED_ORIGINS` on POST requests.
   - **Fix Applied:** Both the Render backend hostname (`geoharmonize-backend-8b1m.onrender.com`) and the Vercel frontend (`https://geoharmonize-xi.vercel.app`) are pre-configured into `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`.

---

## 🛠️ Step-by-Step Render Deployment

### Step 1: Database Setup on Supabase (Free, Permanent PostGIS)
The PostgreSQL database is hosted on **Supabase** (Permanent free tier with native PostGIS, avoids Render's 30-day database deletion policy).
- **Supabase Host:** `db.tyjkryefbludpiebjhvd.supabase.co`
- **PostGIS Version:** `3.3` (pre-verified and enabled)
- **DATABASE_URL format:**
  `postgresql://postgres:[PASSWORD]@db.tyjkryefbludpiebjhvd.supabase.co:5432/postgres?sslmode=require`

### Step 2: Configure the Backend Web Service on Render
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your repository: `https://github.com/sarveshsuyal/Geoharmonize` (branch `main`).
3. Set the service properties:
   - **Name:** `geoharmonize-backend-8b1m` (or your chosen service name)
   - **Runtime:** `Docker` *(Do NOT select Python! Docker is required for C-GDAL libraries)*
   - **Dockerfile Path:** `./Dockerfile`
   - **Docker Context:** `.`
   - **Health Check Path:** `/health/`
   - **Plan:** Free
4. Under **Environment Variables**, configure:

| Key | Value | Notes |
| :--- | :--- | :--- |
| `DATABASE_URL` | `[Paste Render Internal Database URL]` | Connection to PostgreSQL + PostGIS |
| `DJANGO_SECRET_KEY` | `[Click Generate to create random key]` | Django session cryptographic key |
| `DJANGO_DEBUG` | `False` | Disables debug mode in production |
| `DJANGO_ALLOWED_HOSTS` | `.onrender.com,geoharmonize-backend-8b1m.onrender.com,localhost,127.0.0.1` | Host header security |
| `FRONTEND_URL` | `https://geoharmonize-xi.vercel.app` | Primary frontend origin |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,https://geoharmonize-xi.vercel.app` | Explicit CORS permissions |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:5173,https://geoharmonize-xi.vercel.app,https://geoharmonize-backend-8b1m.onrender.com` | Trusted origins for CSRF POSTs |
| `PROJECT_TARGET_CRS` | `EPSG:32644` | Target harmonization CRS |
| `BOOTSTRAP_ADMIN` | `true` *(first run only)* | Set to `true` to auto-create admin account |
| `ADMIN_USERNAME` | `admin` | Your desired admin username |
| `ADMIN_EMAIL` | `admin@geoharmonize.gov.in` | Your desired admin email |
| `ADMIN_PASSWORD` | `[Your-Secure-Password-Min-12-Chars]` | Your administrator password |

5. Click **Create Web Service** (or **Manual Deploy** > **Deploy latest commit**).

---

## 🌐 Verifying Your Deployment

### 1. Health Check Endpoint
Once deployed, verify:
```bash
curl -i https://geoharmonize-backend-8b1m.onrender.com/health/
```
Expected HTTP 200 response:
```json
{
  "status": "healthy",
  "service": "geoharmonize-api",
  "version": "1.0.0",
  "database": {
    "connected": true,
    "postgis_ready": true,
    "postgis_version": "3.4.x ...",
    "error": null,
    "postgis_error": null
  }
}
```

### 2. Django Admin Portal
Visit `https://geoharmonize-backend-8b1m.onrender.com/admin/` and log in with your configured administrator credentials.

### 3. Vercel Frontend Connection
The frontend at `https://geoharmonize-xi.vercel.app/` connects to `https://geoharmonize-backend-8b1m.onrender.com/api` by default in production.
To verify:
1. Open https://geoharmonize-xi.vercel.app/
2. Check the live status pill in the top header. When the Render instance is awake, it will turn green: `Render Cloud (xxx ms)`.
3. Sign in to the console with your administrator credentials.

---

## 💡 Note on Render Free Tier "Cold Starts"

On Render's Free tier, web services spin down after 15 minutes of inactivity. When a request arrives, wake-up requires **30 to 50 seconds**.

The GeoHarmonize login page includes an automated **live backend ping detector** and **cold-start alert banner** to inform users while Render spins up the container.
