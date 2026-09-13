from django.urls import path
from .views import (
    HarmonizationSummaryReportView, ConflictReportView, DatasetValidationReportView,
    ParcelMatchingReportView, ChangeDetectionReportView,
)

urlpatterns = [
    path("harmonization-summary/<int:run_id>/", HarmonizationSummaryReportView.as_view(), name="report-harmonization-summary"),
    path("conflicts/", ConflictReportView.as_view(), name="report-conflicts"),
    path("dataset-validation/", DatasetValidationReportView.as_view(), name="report-dataset-validation"),
    path("parcel-matching/", ParcelMatchingReportView.as_view(), name="report-parcel-matching"),
    path("change-detection/<int:run_id>/", ChangeDetectionReportView.as_view(), name="report-change-detection"),
]
