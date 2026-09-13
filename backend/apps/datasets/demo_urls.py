from django.urls import path
from .demo_views import RunDemoView

urlpatterns = [
    path("run/", RunDemoView.as_view(), name="demo-run"),
]
