import logging

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import CanUploadOrProcess
from .models import Dataset, ProcessingStatus
from .serializers import DatasetSerializer, ManualCRSSerializer, ProcessingLogSerializer
from .services.ingestion_service import IngestionService, IngestionError

logger = logging.getLogger("geoharmonize")


class DatasetViewSet(viewsets.ModelViewSet):
    """
    /api/datasets/                 GET list, POST upload
    /api/datasets/{id}/            GET detail, DELETE
    /api/datasets/{id}/validate/   POST -> re-run validation
    /api/datasets/{id}/process/    POST -> run downstream feature extraction (vector import / CV pipeline)
    /api/datasets/{id}/set-crs/    POST -> manually specify CRS when auto-detection failed
    /api/datasets/{id}/logs/       GET  -> processing log trail
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [CanUploadOrProcess]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["dataset_type", "processing_status"]
    search_fields = ["name", "source"]
    ordering_fields = ["created_at", "name", "feature_count"]

    def perform_create(self, serializer):
        dataset = serializer.save()
        try:
            IngestionService().process_new_dataset(dataset)
        except IngestionError:
            # Error is already stored on the dataset (status=FAILED, error_message set).
            # We don't raise an HTTP error for the upload itself - the client can see
            # the failure reason on the returned resource.
            pass

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        dataset = self.get_object()
        try:
            IngestionService().process_new_dataset(dataset)
        except IngestionError as e:
            return Response({"code": e.code, "message": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DatasetSerializer(dataset).data)

    @action(detail=True, methods=["post"], url_path="set-crs")
    def set_crs(self, request, pk=None):
        dataset = self.get_object()
        serializer = ManualCRSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        IngestionService().set_manual_crs(dataset, serializer.validated_data["crs"])
        return Response(DatasetSerializer(dataset).data)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        """
        Runs feature extraction appropriate to the dataset type:
          - vector datasets -> import into PostGIS-backed feature tables (parcels/buildings/roads/utilities)
          - imagery datasets -> AI/CV pipeline (apps.ai)
        """
        dataset = self.get_object()
        if dataset.processing_status == ProcessingStatus.PROCESSED:
            return Response({
                "dataset": DatasetSerializer(dataset).data,
                "result": {"already_processed": True},
            })
        if dataset.processing_status == ProcessingStatus.NEEDS_CRS:
            return Response(
                {"code": "INVALID_CRS",
                 "message": "The uploaded dataset does not contain a valid coordinate reference system. "
                            "Please specify the CRS before processing."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dataset.processing_status = ProcessingStatus.PROCESSING
        dataset.save(update_fields=["processing_status"])

        try:
            if dataset.geometry_type == "RASTER":
                from apps.ai.services.feature_extractor import OpenCVFeatureExtractor
                extractor = OpenCVFeatureExtractor()
                result = extractor.extract(dataset)
            else:
                from apps.geospatial.services.vector_service import VectorImportService
                result = VectorImportService().import_dataset(dataset)

            dataset.processing_status = ProcessingStatus.PROCESSED
            dataset.save(update_fields=["processing_status"])
            return Response({"dataset": DatasetSerializer(dataset).data, "result": result})
        except Exception as e:  # noqa: BLE001
            logger.exception("Dataset processing failed")
            dataset.processing_status = ProcessingStatus.FAILED
            dataset.error_message = str(e)
            dataset.save(update_fields=["processing_status", "error_message"])
            return Response({"code": "PROCESSING_FAILED", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        dataset = self.get_object()
        return Response(ProcessingLogSerializer(dataset.logs.all(), many=True).data)
