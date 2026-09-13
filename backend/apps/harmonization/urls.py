from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import HarmonizationRunViewSet, RunHarmonizationView, ParcelMatchViewSet, AttributeMappingRuleViewSet

router = DefaultRouter()
router.register("runs", HarmonizationRunViewSet, basename="harmonization-run")
router.register("matches", ParcelMatchViewSet, basename="parcel-match")
router.register("attribute-mappings", AttributeMappingRuleViewSet, basename="attribute-mapping")

urlpatterns = [
    path("run/", RunHarmonizationView.as_view(), name="harmonization-start"),
] + router.urls
