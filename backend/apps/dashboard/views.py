"""
Real-time dashboard statistics computed directly from the database -
never hard-coded, per the problem statement's explicit requirement.
"""
from django.db.models import Avg, Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.datasets.models import Dataset
        from apps.parcels.models import Parcel
        from apps.conflicts.models import Conflict
        from apps.harmonization.models import ParcelMatch, HarmonizationRun

        total_datasets = Dataset.objects.count()
        total_parcels = Parcel.objects.count()
        matched_parcels = ParcelMatch.objects.filter(status="MATCHED").count()
        unmatched_parcels = Parcel.objects.filter(is_harmonized=False).count()

        conflicts_qs = Conflict.objects.all()
        total_conflicts = conflicts_qs.count()
        resolved_conflicts = conflicts_qs.filter(status__in=["ACCEPTED", "AUTO_RESOLVED"]).count()
        pending_reviews = conflicts_qs.filter(status__in=["PENDING", "FIELD_VERIFICATION"]).count()

        avg_confidence = Parcel.objects.aggregate(avg=Avg("confidence_score"))["avg"] or 0

        by_severity = dict(conflicts_qs.values_list("severity").annotate(c=Count("id")))
        by_type = dict(conflicts_qs.values_list("conflict_type").annotate(c=Count("id")))
        by_dataset_type = dict(Dataset.objects.values_list("dataset_type").annotate(c=Count("id")))

        latest_run = HarmonizationRun.objects.order_by("-started_at").first()

        return Response({
            "total_datasets": total_datasets,
            "total_parcels": total_parcels,
            "matched_parcels": matched_parcels,
            "unmatched_parcels": unmatched_parcels,
            "conflicts": total_conflicts,
            "resolved_conflicts": resolved_conflicts,
            "pending_reviews": pending_reviews,
            "average_confidence": round(avg_confidence, 1),
            "conflicts_by_severity": by_severity,
            "conflicts_by_type": by_type,
            "datasets_by_type": by_dataset_type,
            "latest_run": {
                "id": latest_run.id, "status": latest_run.status, "progress": latest_run.progress,
                "statistics": latest_run.statistics,
            } if latest_run else None,
        })
