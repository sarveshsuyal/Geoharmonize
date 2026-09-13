from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanUploadOrProcess
from .models import ChangeDetectionRun, ChangeFeature
from .serializers import ChangeDetectionRunSerializer, RunChangeDetectionSerializer


class ChangeDetectionRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ChangeDetectionRun.objects.all()
    serializer_class = ChangeDetectionRunSerializer
    permission_classes = [permissions.IsAuthenticated]


class RunChangeDetectionView(APIView):
    permission_classes = [CanUploadOrProcess]

    def post(self, request):
        serializer = RunChangeDetectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.datasets.models import Dataset
        from apps.parcels.models import Parcel
        from apps.ai.services.change_detector import VectorChangeDetector
        from shapely import wkt as shapely_wkt

        before_ds = Dataset.objects.get(pk=serializer.validated_data["dataset_before_id"])
        after_ds = Dataset.objects.get(pk=serializer.validated_data["dataset_after_id"])

        run = ChangeDetectionRun.objects.create(dataset_before=before_ds, dataset_after=after_ds, status="PENDING")
        try:
            before_features = [(p.id, shapely_wkt.loads(p.geometry.wkt))
                               for p in Parcel.objects.filter(source_datasets=before_ds).exclude(geometry=None)]
            after_features = [(p.id, shapely_wkt.loads(p.geometry.wkt))
                              for p in Parcel.objects.filter(source_datasets=after_ds).exclude(geometry=None)]

            records = VectorChangeDetector().compare(before_features, after_features)

            stats = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
            for r in records:
                ChangeFeature.objects.create(
                    run=run, feature_kind="PARCEL", change_type=r.change_type,
                    geometry_before=r.geometry_before_wkt, geometry_after=r.geometry_after_wkt, iou=r.iou,
                )
                stats[r.change_type.lower()] += 1

            run.status = "COMPLETED"
            run.statistics = stats
            run.save()
            return Response(ChangeDetectionRunSerializer(run).data, status=status.HTTP_201_CREATED)
        except Exception as e:  # noqa: BLE001
            run.status = "FAILED"
            run.error_message = str(e)
            run.save()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
