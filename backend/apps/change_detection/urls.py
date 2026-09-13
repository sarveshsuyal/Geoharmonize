from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ChangeDetectionRunViewSet, RunChangeDetectionView

router = DefaultRouter()
router.register("runs", ChangeDetectionRunViewSet, basename="change-detection-run")

urlpatterns = [
    path("run/", RunChangeDetectionView.as_view(), name="change-detection-start"),
] + router.urls
