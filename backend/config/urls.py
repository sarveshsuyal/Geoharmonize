"""
GeoHarmonize root URL configuration.
Each app owns its own urls.py; this file only mounts them under /api/.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "geoharmonize-api",
        "version": "0.1.0"
    })

urlpatterns = [
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
