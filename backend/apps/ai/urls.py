from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    AIAnalyzeView,
    AIAnalysisRunViewSet,
    AIAnalysisGeoJSONView,
    AIRecommendationsGeoJSONView,
)

router = DefaultRouter()
router.register(r"analyses", AIAnalysisRunViewSet, basename="ai-analyses")

urlpatterns = [
    path("analyze/", AIAnalyzeView.as_view(), name="ai-analyze"),
    path("analyses/<int:pk>/geojson/", AIAnalysisGeoJSONView.as_view(), name="ai-analysis-geojson"),
    path("analyses/<int:pk>/recommendations/geojson/", AIRecommendationsGeoJSONView.as_view(), name="ai-recommendations-geojson"),
] + router.urls
