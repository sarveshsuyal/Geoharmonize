from django.urls import path
from .views import LayersSummaryView

urlpatterns = [
    path("layers/", LayersSummaryView.as_view(), name="geospatial-layers"),
]
