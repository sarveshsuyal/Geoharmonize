from django.contrib.gis.geos import Polygon
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Parcel, Building, Road, Utility
from .serializers import (
    ParcelGeoSerializer, ParcelDetailSerializer,
    BuildingGeoSerializer, RoadGeoSerializer, UtilityGeoSerializer,
)


class BBoxMixin:
    def filter_by_bbox(self, qs):
        bbox = self.request.query_params.get("bbox")
        if not bbox:
            return qs
        try:
            minx, miny, maxx, maxy = [float(v) for v in bbox.split(",")]
        except ValueError:
            return qs
        return qs.filter(geometry__bboverlaps=Polygon.from_bbox((minx, miny, maxx, maxy)))


class ParcelViewSet(BBoxMixin, viewsets.ReadOnlyModelViewSet):
    """
    GET /api/parcels/                 -> list (paginated, plain JSON)
    GET /api/parcels/{id}/            -> detail with provenance/land record/conflicts
    GET /api/parcels/geojson/         -> bbox-filtered FeatureCollection for the map
    """
    queryset = Parcel.objects.all().prefetch_related("source_datasets").select_related("land_record")
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["validation_status", "is_harmonized", "land_use", "source_datasets"]
    search_fields = ["parcel_id", "survey_number", "property_reference"]

    def get_queryset(self):
        qs = super().get_queryset()
        dataset_id = self.request.query_params.get("dataset_id")
        if dataset_id:
            qs = qs.filter(source_datasets__id=dataset_id)

        unmatched = self.request.query_params.get("unmatched")
        if unmatched and unmatched.lower() in ("true", "1"):
            qs = qs.filter(is_harmonized=False, matches_as_source__isnull=True, matches_as_target__isnull=True)

        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ParcelDetailSerializer
        return ParcelGeoSerializer

    @action(detail=False, methods=["get"])
    def geojson(self, request):
        qs = self.filter_by_bbox(self.filter_queryset(self.get_queryset()))[:2000]
        return Response(ParcelGeoSerializer(qs, many=True).data)


class BuildingViewSet(BBoxMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingGeoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def geojson(self, request):
        qs = self.filter_by_bbox(self.get_queryset())[:2000]
        return Response(BuildingGeoSerializer(qs, many=True).data)


class RoadViewSet(BBoxMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Road.objects.all()
    serializer_class = RoadGeoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def geojson(self, request):
        qs = self.filter_by_bbox(self.get_queryset())[:2000]
        return Response(RoadGeoSerializer(qs, many=True).data)


class UtilityViewSet(BBoxMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Utility.objects.all()
    serializer_class = UtilityGeoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def geojson(self, request):
        qs = self.filter_by_bbox(self.get_queryset())[:2000]
        return Response(UtilityGeoSerializer(qs, many=True).data)
