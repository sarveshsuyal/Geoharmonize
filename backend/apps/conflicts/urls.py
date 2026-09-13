from rest_framework.routers import DefaultRouter
from .views import ConflictViewSet

router = DefaultRouter()
router.register("", ConflictViewSet, basename="conflict")
urlpatterns = router.urls
