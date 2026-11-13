
"""
GeoHarmonize - Production Django Configuration
SIH26013 | Department of Land Resources

Production:
    Render + PostgreSQL/PostGIS + Gunicorn

Development:
    Docker Compose + PostgreSQL/PostGIS

Requirements:
    Python 3.12
    GDAL
    GeoDjango
"""

import os
import logging
from pathlib import Path
from datetime import timedelta

import dj_database_url


# ==========================================================
# 1. BASE CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None, cast=str):
    """Read and safely cast environment variables."""
    value = os.environ.get(key, default)

    if value is None:
        return None

    if cast is bool:
        return str(value).strip().lower() in {
            "1", "true", "yes", "on"
        }

    if cast is int:
        return int(value)

    return value


def env_list(key, default=""):
    """Read comma-separated environment variables."""
    return [
        item.strip()
        for item in env(key, default).split(",")
        if item.strip()
    ]


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


# ==========================================================
# 2. SECURITY AND ENVIRONMENT
# ==========================================================

DEBUG = env("DJANGO_DEBUG", "False", bool)

SECRET_KEY = env("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "local-development-only-insecure-key"
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY is required in production."
        )

if not DEBUG and SECRET_KEY == "local-development-only-insecure-key":
    raise RuntimeError(
        "An insecure development SECRET_KEY cannot be used in production."
    )


IS_RENDER = env("RENDER", "False", bool)

render_external_host = env("RENDER_EXTERNAL_HOSTNAME")


# ==========================================================
# 3. ALLOWED HOSTS
# ==========================================================

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,0.0.0.0,backend,frontend,.onrender.com,geoharmonize-backend-8b1m.onrender.com"
)

if render_external_host:
    add_unique(ALLOWED_HOSTS, render_external_host)
elif IS_RENDER and not any(".onrender.com" in host for host in ALLOWED_HOSTS):
    raise RuntimeError(
        "RENDER_EXTERNAL_HOSTNAME is missing and no Render host configured in DJANGO_ALLOWED_HOSTS."
    )

if "*" in ALLOWED_HOSTS:
    raise RuntimeError(
        "Wildcard ALLOWED_HOSTS is not permitted."
    )


# ==========================================================
# 4. APPLICATION REGISTRATION
# ==========================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",

    # Third-party
    "rest_framework",
    "rest_framework_gis",
    "corsheaders",
    "django_filters",

    # GeoHarmonize applications
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


# ==========================================================
# 5. MIDDLEWARE
# ==========================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==========================================================
# 6. DJANGO APPLICATION CONFIGURATION
# ==========================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"

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


# ==========================================================
# 7. DATABASE - POSTGRESQL / POSTGIS
# ==========================================================

database_url = env("DATABASE_URL")

if database_url:

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    is_local_db = any(
        host in database_url
        for host in [
            "localhost",
            "127.0.0.1",
            "db:5432",
        ]
    )

    ssl_needed = env(
        "DB_SSL_REQUIRE",
        "False" if is_local_db else "True",
        bool
    )

    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            engine="django.contrib.gis.db.backends.postgis",
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=ssl_needed,
        )
    }

elif IS_RENDER:

    raise RuntimeError(
        "DATABASE_URL is required for Render production."
    )

elif env("USE_SQLITE", "False", bool):

    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.spatialite",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

    spatialite_path = env("SPATIALITE_LIBRARY_PATH")

    if spatialite_path:
        SPATIALITE_LIBRARY_PATH = spatialite_path

else:

    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": env("POSTGRES_DB", "geoharmonize"),
            "USER": env("POSTGRES_USER", "geoharmonize"),
            "PASSWORD": env("POSTGRES_PASSWORD", "geoharmonize"),
            "HOST": env("POSTGRES_HOST", "db"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
        }
    }


# ==========================================================
# 8. GEOSPATIAL LIBRARY CONFIGURATION
# ==========================================================

GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH")

GEOS_LIBRARY_PATH = env("GEOS_LIBRARY_PATH")


# ==========================================================
# 9. AUTHENTICATION
# ==========================================================

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


# ==========================================================
# 10. LANGUAGE AND TIMEZONE
# ==========================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


# ==========================================================
# 11. STATIC AND MEDIA FILES
# ==========================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Upload limits
MAX_UPLOAD_SIZE_MB = env("MAX_UPLOAD_SIZE_MB", 200, int)

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ==========================================================
# 12. DEFAULT MODEL FIELD
# ==========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==========================================================
# 13. DJANGO REST FRAMEWORK
# ==========================================================

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

    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),

    "PAGE_SIZE": 50,

    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
}


# ==========================================================
# 14. JWT AUTHENTICATION
# ==========================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),

    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    "ROTATE_REFRESH_TOKENS": False,

    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ==========================================================
# 15. CORS CONFIGURATION
# ==========================================================

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174,"
        "http://localhost:3000,"
        "https://geoharmonize-xi.vercel.app"
    )
)

# Optional explicit preview-domain patterns.
CORS_ALLOWED_ORIGIN_REGEXES = env_list(
    "CORS_ALLOWED_ORIGIN_REGEXES",
    ""
)


# ==========================================================
# 16. CSRF CONFIGURATION
# ==========================================================

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    (
        "http://localhost:5173,"
        "http://localhost:5174,"
        "http://localhost:3000,"
        "https://geoharmonize-xi.vercel.app,"
        "https://geoharmonize-backend-8b1m.onrender.com"
    )
)

# Add explicitly configured frontend origin.
frontend_url = env("FRONTEND_URL", "https://geoharmonize-xi.vercel.app")

if frontend_url:
    add_unique(CORS_ALLOWED_ORIGINS, frontend_url.rstrip("/"))
    add_unique(CSRF_TRUSTED_ORIGINS, frontend_url.rstrip("/"))

# Allow backend host itself for Django Admin CSRF verification on Render
if render_external_host:
    add_unique(CSRF_TRUSTED_ORIGINS, f"https://{render_external_host}")


# ==========================================================
# 17. PRODUCTION HTTPS SECURITY
# ==========================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https"
)

SECURE_SSL_REDIRECT = env(
    "SECURE_SSL_REDIRECT",
    not DEBUG,
    bool
)

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = False

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"

# Enable HSTS only after confirming HTTPS works correctly.
SECURE_HSTS_SECONDS = env(
    "SECURE_HSTS_SECONDS",
    0,
    int
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    SECURE_HSTS_SECONDS > 0
)

SECURE_HSTS_PRELOAD = False


# ==========================================================
# 18. GEOHARMONIZE APPLICATION CONFIGURATION
# ==========================================================

GEOHARMONIZE = {
    "PROJECT_TARGET_CRS": env(
        "PROJECT_TARGET_CRS",
        "EPSG:32644"
    ),

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
        "GNSS": 95,
        "CADASTRAL": 85,
        "DRONE": 80,
        "MUNICIPAL": 65,
        "SATELLITE": 60,
        "REVENUE": 70,
        "CROWD": 30,
        "OTHER": 40,
    },

    "MAX_UPLOAD_SIZE_MB": MAX_UPLOAD_SIZE_MB,

    "MATCH_ACCEPT_THRESHOLD": 60,
}


# ==========================================================
# 19. LOGGING
# ==========================================================

LOG_LEVEL = env(
    "DJANGO_LOG_LEVEL",
    "DEBUG" if DEBUG else "INFO"
).upper()

LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": (
                "[{asctime}] {levelname} "
                "{name}: {message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },

    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },

    "loggers": {
        "geoharmonize": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

