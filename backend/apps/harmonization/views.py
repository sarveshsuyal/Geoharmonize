import json
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import CanUploadOrProcess, CanResolveConflicts
from .models import (
    HarmonizationRun, ParcelMatch, ParcelMatchReviewAction, AttributeMappingRule,
    RunStatus, MatchStatus,
)
from .serializers import (
    HarmonizationRunSerializer, StartHarmonizationSerializer,
    ParcelMatchSerializer, ParcelMatchDetailSerializer,
    ReviewMatchActionSerializer, AttributeMappingRuleSerializer,
)
from .services.pipeline_service import HarmonizationPipeline
from .services.export_service import HarmonizedExportService


class HarmonizationRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/harmonization/runs/            -> list runs
    GET  /api/harmonization/runs/{id}/       -> poll run status/progress
    POST /api/harmonization/run/             -> start a new run
    GET  /api/harmonization/runs/{id}/results/ -> candidate pairs for review
    GET  /api/harmonization/runs/{id}/output/  -> GeoJSON FeatureCollection of harmonized layer
    GET  /api/harmonization/runs/{id}/export/  -> downloadable GeoJSON attachment
    GET  /api/harmonization/runs/{id}/conflicts/ -> conflicts detected in run
    """
    queryset = HarmonizationRun.objects.all()
    serializer_class = HarmonizationRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        run = self.get_object()
        matches = run.matches.select_related("source_parcel", "target_parcel").all()
        status_param = request.query_params.get("status")
        if status_param:
            matches = matches.filter(status=status_param)
        return Response(ParcelMatchDetailSerializer(matches, many=True).data)

    @action(detail=True, methods=["get"])
    def output(self, request, pk=None):
        run = self.get_object()
        geojson_data = HarmonizedExportService().generate_harmonized_geojson(run)
        if not HarmonizedExportService().verify_geojson(geojson_data):
            return Response({"detail": "Generated GeoJSON failed geometry validation."}, status=500)
        return Response(geojson_data)

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        run = self.get_object()
        geojson_data = HarmonizedExportService().generate_harmonized_geojson(run)
        if not HarmonizedExportService().verify_geojson(geojson_data):
            return Response({"detail": "Generated GeoJSON failed geometry validation."}, status=500)
        content = json.dumps(geojson_data, indent=2)
        response = HttpResponse(content, content_type="application/geo+json")
        response["Content-Disposition"] = f'attachment; filename="harmonized_run_{run.id}.geojson"'
        return response

    @action(detail=True, methods=["get"])
    def conflicts(self, request, pk=None):
        run = self.get_object()
        from apps.conflicts.models import Conflict
        from apps.conflicts.serializers import ConflictListSerializer
        conflicts = Conflict.objects.filter(run=run)
        return Response(ConflictListSerializer(conflicts, many=True).data)


class RunHarmonizationView(APIView):
    permission_classes = [CanUploadOrProcess]

    def post(self, request):
        serializer = StartHarmonizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dataset_ids = serializer.validated_data["dataset_ids"]

        run = HarmonizationRun.objects.create(status=RunStatus.PENDING, dataset_ids=dataset_ids)
        try:
            stats = HarmonizationPipeline(run).run_pipeline(dataset_ids)
        except Exception as e:  # noqa: BLE001
            return Response(
                {"run_id": run.id, "status": "FAILED", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(HarmonizationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ParcelMatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/harmonization/matches/                 -> list matches
    GET  /api/harmonization/matches/{id}/            -> match detail
    POST /api/harmonization/matches/{id}/review/     -> human decision (ACCEPT/REJECT/CHOOSE_ALT/CONFIRM_SPLIT/MERGE)
    """
    queryset = ParcelMatch.objects.select_related("source_parcel", "target_parcel").all()
    serializer_class = ParcelMatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["run", "status", "relationship_type"]

    def get_serializer_class(self):
        if self.action in ("retrieve", "review"):
            return ParcelMatchDetailSerializer
        return ParcelMatchSerializer

    @action(detail=True, methods=["post"], permission_classes=[CanResolveConflicts])
    def review(self, request, pk=None):
        match = self.get_object()
        serializer = ReviewMatchActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        action_type = data["action"]
        notes = data.get("notes", "")
        alt_target_id = data.get("alternative_target_id")
        previous_status = match.status

        if action_type == "ACCEPT":
            match.status = MatchStatus.MATCH
            match.source_parcel.is_harmonized = True
            match.source_parcel.save(update_fields=["is_harmonized"])
            match.source_parcel.harmonized_from.add(match.target_parcel)

        elif action_type == "REJECT":
            match.status = MatchStatus.REJECTED

        elif action_type == "MARK_UNRESOLVED":
            match.status = MatchStatus.REVIEW
            match.relationship_type = "UNRESOLVED"

        elif action_type == "CONFIRM_SPLIT":
            match.status = MatchStatus.SPLIT
            match.relationship_type = "SPLIT"

        elif action_type == "CONFIRM_MERGE":
            match.status = MatchStatus.MERGE
            match.relationship_type = "MERGE"

        elif action_type == "CHOOSE_ALTERNATIVE":
            if not alt_target_id:
                return Response(
                    {"detail": "alternative_target_id is required for CHOOSE_ALTERNATIVE"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from apps.parcels.models import Parcel
            from shapely import wkt as shapely_wkt
            from .services.matching_service import MatchingService
            try:
                new_tgt = Parcel.objects.get(pk=alt_target_id)
                match.target_parcel = new_tgt
                if match.source_parcel.geometry and new_tgt.geometry:
                    ga = shapely_wkt.loads(match.source_parcel.geometry.wkt)
                    gb = shapely_wkt.loads(new_tgt.geometry.wkt)
                    m_metrics = MatchingService().compute_metrics(ga, gb)
                    if m_metrics:
                        match.overlap_ratio = m_metrics.overlap_ratio
                        match.area_similarity = m_metrics.area_similarity
                        match.centroid_distance_m = m_metrics.centroid_distance_m
                        match.shape_similarity = m_metrics.shape_similarity
                        match.boundary_similarity = m_metrics.boundary_similarity
                        match.topology_relationship = m_metrics.topology_relationship
                match.status = MatchStatus.MATCH
            except Parcel.DoesNotExist:
                return Response({"detail": "Alternative parcel not found."}, status=status.HTTP_404_NOT_FOUND)

        match.review_decision = action_type
        match.review_notes = notes
        match.reviewed_by = request.user
        match.reviewed_at = timezone.now()
        match.save()
        ParcelMatchReviewAction.objects.create(
            match=match,
            action=action_type,
            reason=notes,
            performed_by=request.user,
            previous_status=previous_status,
            resulting_status=match.status,
        )

        if action_type == "REJECT":
            from apps.parcels.models import Parcel
            if not ParcelMatch.objects.filter(
                source_parcel=match.source_parcel,
                status__in=[MatchStatus.MATCH, MatchStatus.SPLIT, MatchStatus.MERGE],
            ).exists():
                match.source_parcel.is_harmonized = False
                match.source_parcel.harmonized_from.clear()
                match.source_parcel.save(update_fields=["is_harmonized"])

        return Response(ParcelMatchDetailSerializer(match).data)


class AttributeMappingRuleViewSet(viewsets.ModelViewSet):
    queryset = AttributeMappingRule.objects.all()
    serializer_class = AttributeMappingRuleSerializer
    permission_classes = [CanUploadOrProcess]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
