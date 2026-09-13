from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.report_service import ReportService


class BaseReportView(APIView):
    permission_classes = [IsAuthenticated]
    report_service = ReportService()

    def csv_response(self, csv_text, filename):
        resp = HttpResponse(csv_text, content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


class HarmonizationSummaryReportView(BaseReportView):
    def get(self, request, run_id):
        from apps.harmonization.models import HarmonizationRun
        run = HarmonizationRun.objects.get(pk=run_id)
        csv_text = self.report_service.harmonization_summary_csv(run)
        return self.csv_response(csv_text, f"harmonization_summary_{run_id}.csv")


class ConflictReportView(BaseReportView):
    def get(self, request):
        from apps.conflicts.models import Conflict
        csv_text = self.report_service.conflict_report_csv(Conflict.objects.all())
        return self.csv_response(csv_text, "conflict_report.csv")


class DatasetValidationReportView(BaseReportView):
    def get(self, request):
        from apps.datasets.models import Dataset
        csv_text = self.report_service.dataset_validation_report_csv(Dataset.objects.all())
        return self.csv_response(csv_text, "dataset_validation_report.csv")


class ParcelMatchingReportView(BaseReportView):
    def get(self, request):
        from apps.harmonization.models import ParcelMatch
        csv_text = self.report_service.parcel_matching_report_csv(ParcelMatch.objects.select_related("source_parcel", "target_parcel"))
        return self.csv_response(csv_text, "parcel_matching_report.csv")


class ChangeDetectionReportView(BaseReportView):
    def get(self, request, run_id):
        from apps.change_detection.models import ChangeDetectionRun
        run = ChangeDetectionRun.objects.get(pk=run_id)
        csv_text = self.report_service.change_detection_report_csv(run)
        return self.csv_response(csv_text, f"change_detection_report_{run_id}.csv")
