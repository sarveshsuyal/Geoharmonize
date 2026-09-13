from rest_framework.routers import DefaultRouter
from .views import ParcelViewSet, BuildingViewSet, RoadViewSet, UtilityViewSet

router = DefaultRouter()
router.register("buildings", BuildingViewSet, basename="building")
router.register("roads", RoadViewSet, basename="road")
router.register("utilities", UtilityViewSet, basename="utility")
router.register("", ParcelViewSet, basename="parcel")
urlpatterns = router.urls
