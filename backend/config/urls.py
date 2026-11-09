"""
GeoHarmonize root URL configuration.
Each app owns its own urls.py; this file only mounts them under /api/.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

from django.db import connection

def health_check(request):
    db_ok = False
    postgis_ok = False
    db_error = None
    postgis_version = None

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            db_ok = True
            try:
                cursor.execute("SELECT PostGIS_Full_Version();")
                row = cursor.fetchone()
                if row:
                    postgis_version = row[0]
                    postgis_ok = True
            except Exception as pe:
                postgis_error = str(pe)
    except Exception as exc:
        db_error = str(exc)

    return JsonResponse({
        "status": "ok" if db_ok else "initializing",
        "service": "geoharmonize-api",
        "version": "1.0.0",
        "platform": "Render / Docker Cloud",
        "database": {
            "connected": db_ok,
            "postgis_ready": postgis_ok,
            "postgis_version": postgis_version,
            "error": db_error,
        },
        "endpoints": {
            "auth": "/api/auth/token/",
            "datasets": "/api/datasets/",
            "parcels": "/api/parcels/",
            "harmonization": "/api/harmonization/",
            "conflicts": "/api/conflicts/",
            "change_detection": "/api/change-detection/",
            "dashboard": "/api/dashboard/stats/",
            "reports": "/api/reports/",
            "demo": "/api/demo/run/",
            "health": "/health/",
        }
    })

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
