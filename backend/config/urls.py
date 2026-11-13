"""
GeoHarmonize root URL configuration.
Each app owns its own urls.py; this file only mounts them under /api/.
"""
import logging
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection

logger = logging.getLogger("geoharmonize")


def health_check(request):
    db_ok = False
    postgis_ok = False
    db_error = None
    postgis_error = None
    postgis_version = None

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = True

            try:
                cursor.execute("SELECT PostGIS_Full_Version()")
                row = cursor.fetchone()

                if row:
                    postgis_version = row[0]
                    postgis_ok = True

            except Exception as exc:
                logger.error("PostGIS verification failed: %s", exc)
                postgis_error = str(exc) if settings.DEBUG else "PostGIS check failed"

    except Exception as exc:
        logger.error("Database connectivity check failed: %s", exc)
        db_error = str(exc) if settings.DEBUG else "Database connection failed"

    ready = db_ok and postgis_ok

    return JsonResponse(
        {
            "status": "healthy" if ready else "not_ready",
            "service": "geoharmonize-api",
            "version": "1.0.0",

            "database": {
                "connected": db_ok,
                "postgis_ready": postgis_ok,
                "postgis_version": postgis_version,
                "error": db_error,
                "postgis_error": postgis_error,
            },

            "endpoints": {
                "auth": "/api/auth/",
                "datasets": "/api/datasets/",
                "geospatial": "/api/geospatial/",
                "parcels": "/api/parcels/",
                "harmonization": "/api/harmonization/",
                "conflicts": "/api/conflicts/",
                "change_detection": "/api/change-detection/",
                "ai": "/api/ai/",
                "dashboard": "/api/dashboard/",
                "reports": "/api/reports/",
                "demo": "/api/demo/",
                "health": "/health/",
            },
        },
        status=200 if ready else 503,
    )

urlpatterns = [
    path("", health_check, name="root-health"),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="api-health-check"),
    path("health/", health_check, name="health-check"),

    path("api/auth/", include("apps.accounts.urls")),
    path("api/datasets/", include("apps.datasets.urls")),
    path("api/geospatial/", include("apps.geospatial.urls")),
    path("api/parcels/", include("apps.parcels.urls")),

    path("api/harmonization/", include("apps.harmonization.urls")),
    path("api/conflicts/", include("apps.conflicts.urls")),
    path("api/change-detection/", include("apps.change_detection.urls")),
    path("api/ai/", include("apps.ai.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/demo/", include("apps.datasets.demo_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
