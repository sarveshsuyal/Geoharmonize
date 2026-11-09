"""
GeoHarmonize - Django settings.
Prototype for SIH26013 (Department of Land Resources, Ministry of Rural Development).

Run modes:
- Uses environment variables (see .env.example). Never hard-code secrets.
- Requires GDAL to be installed on the OS for GeoDjango (see Dockerfile).
"""
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

def env(key, default=None, cast=str):
    val = os.environ.get(key, default)
    if val is None:
        return None
    if cast is bool:
        return str(val).lower() in ("1", "true", "yes", "on")
    if cast is int:
        return int(val)
    return val

SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-secret-change-me")
DEBUG = env("DJANGO_DEBUG", "False", bool)

if not DEBUG and SECRET_KEY == "dev-insecure-secret-change-me":
    import warnings
    warnings.warn(
        "DJANGO_SECRET_KEY is using the insecure default value with DEBUG=False. "
        "Set a strong random DJANGO_SECRET_KEY in production!"
    )

ALLOWED_HOSTS = [
    h.strip()
    for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,backend,frontend").split(",")
    if h.strip()
]

# Auto-detect Render deployment hostname
render_external_host = env("RENDER_EXTERNAL_HOSTNAME")
if render_external_host and render_external_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_external_host)

# Always allow *.onrender.com subdomains so Render health checks and routing never fail
if ".onrender.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".onrender.com")

if env("RENDER", "False", bool) and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",  # GeoDjango

    "rest_framework",
    "rest_framework_gis",
    "corsheaders",
    "django_filters",

    # GeoHarmonize apps
    "apps.accounts",
    "apps.datasets",
    "apps.geospatial",
    "apps.parcels",
    "apps.harmonization",
    "apps.conflicts",
    "apps.ai",
    "apps.change_detection",
    "apps.dashboard",
    "apps.reports",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ------------------------------------------------------------------
# Database - PostgreSQL + PostGIS (Production on Render / Docker)
# Supports DATABASE_URL (Render, Supabase, Neon, AWS RDS, etc.)
# with automatic fallback to POSTGRES_* environment variables.
# ------------------------------------------------------------------
import dj_database_url

database_url = env("DATABASE_URL")
if database_url:
    # Handle postgres:// vs postgresql:// scheme
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    is_local_db = "localhost" in database_url or "127.0.0.1" in database_url or "db:5432" in database_url
    ssl_needed = env("DB_SSL_REQUIRE", "False" if is_local_db else "True", bool)

    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            engine="django.contrib.gis.db.backends.postgis",
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=ssl_needed,
        )
    }
elif env("USE_SQLITE", "False", bool):
    try:
        DATABASES = {
            "default": {
                "ENGINE": "django.contrib.gis.db.backends.spatialite",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
    except Exception:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": env("POSTGRES_DB", "geoharmonize"),
            "USER": env("POSTGRES_USER", "geoharmonize"),
            "PASSWORD": env("POSTGRES_PASSWORD", "geoharmonize"),
            "HOST": env("POSTGRES_HOST", "db"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }

# GDAL/GEOS library paths (used when running outside the provided Docker image,
# e.g. on macOS with Homebrew GDAL). Leave unset inside Docker.
GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH", None)
GEOS_LIBRARY_PATH = env("GEOS_LIBRARY_PATH", None)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
except ImportError:
    pass

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------
# DRF
# ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000",
    ).split(",")
    if o.strip()
]

# Allow all origins by default in production prototype so frontend on Vercel/Netlify can seamlessly call Render backend
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS", "True", bool)

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/.*\.vercel\.app$",
    r"^https:\/\/.*\.onrender\.com$",
    r"^https:\/\/.*\.netlify\.app$",
    r"^https:\/\/.*\.github\.io$",
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in env("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")
    if o.strip()
]

if render_external_host:
    render_origin = f"https://{render_external_host}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

for host in ALLOWED_HOSTS:
    if host not in ("localhost", "127.0.0.1", "0.0.0.0", "*", "backend", "frontend") and not host.startswith("."):
        origin = f"https://{host}"
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

# ------------------------------------------------------------------
# GeoHarmonize application configuration (NOT hard-coded business data -
# these are tunable thresholds / defaults referenced by the services).
# ------------------------------------------------------------------
GEOHARMONIZE = {
    "PROJECT_TARGET_CRS": env("PROJECT_TARGET_CRS", "EPSG:32644"),  # UTM 44N, typical for northern India
    "CONFIDENCE_THRESHOLDS": {
        "HIGH": 85,
        "MEDIUM": 65,
    },
    "SPATIAL_WEIGHT": 0.65,
    "ATTRIBUTE_WEIGHT": 0.35,
    "SPATIAL_METRIC_WEIGHTS": {
        "overlap": 0.35,
        "area": 0.20,
        "centroid": 0.20,
        "shape": 0.15,
        "boundary": 0.10,
    },
    "CLASSIFICATION_THRESHOLDS": {
        "MATCH": 80.0,
        "REVIEW": 55.0,
        "NO_MATCH": 35.0,
    },
    "SPLIT_MERGE_THRESHOLDS": {
        "AREA_SUM_TOLERANCE": 0.25,
        "COVERAGE_THRESHOLD": 0.60,
    },
    "SOURCE_RELIABILITY": {
        # Configurable, not used to auto-resolve legally significant conflicts.
        "GNSS": 95,
        "CADASTRAL": 85,
        "DRONE": 80,
        "MUNICIPAL": 65,
        "SATELLITE": 60,
        "REVENUE": 70,
        "CROWD": 30,
        "OTHER": 40,
    },
    "MAX_UPLOAD_SIZE_MB": env("MAX_UPLOAD_SIZE_MB", "200", int),
    "MATCH_ACCEPT_THRESHOLD": 60,  # below this, a candidate pair is not proposed as a match at all
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "geoharmonize": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
