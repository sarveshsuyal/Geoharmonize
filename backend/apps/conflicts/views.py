from django.contrib.gis.geos import GEOSGeometry
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import CanResolveConflicts
from .models import Conflict, ReviewAction, ConflictStatus
from .serializers import ConflictListSerializer, ConflictDetailSerializer, ResolveConflictSerializer


class ConflictViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/conflicts/                 -> review queue (filterable by type/severity/status)
    GET  /api/conflicts/{id}/            -> full detail incl. both parcel geometries for map overlay
    POST /api/conflicts/{id}/resolve/    -> officer/reviewer decision (Accept/Keep Existing/Edit/Reject/Field Verification)
    """
    queryset = Conflict.objects.select_related("parcel_a", "parcel_b", "dataset_a", "dataset_b").all()
    permission_classes = [CanResolveConflicts]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["conflict_type", "severity", "status"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConflictDetailSerializer
        return ConflictListSerializer

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        conflict = self.get_object()
        serializer = ResolveConflictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        prev_geom_wkt, new_geom_wkt = None, None

        if data["action"] == "ACCEPT":
            conflict.status = ConflictStatus.ACCEPTED
        elif data["action"] == "KEEP_EXISTING":
            conflict.status = ConflictStatus.REJECTED
        elif data["action"] == "REJECT":
            conflict.status = ConflictStatus.REJECTED
        elif data["action"] == "FIELD_VERIFICATION":
            conflict.status = ConflictStatus.FIELD_VERIFICATION
        elif data["action"] == "EDIT_GEOMETRY":
            if not request.user.can_edit_geometry:
                return Response({"detail": "Not permitted to edit geometry."}, status=status.HTTP_403_FORBIDDEN)
            geojson = data.get("new_geometry_geojson")
            if not geojson or not conflict.parcel_a:
                return Response({"detail": "new_geometry_geojson and an associated parcel are required."},
                                 status=status.HTTP_400_BAD_REQUEST)
            import json
            prev_geom_wkt = conflict.parcel_a.geometry.wkt if conflict.parcel_a.geometry else None
            new_geom = GEOSGeometry(json.dumps(geojson))
            conflict.parcel_a.geometry = new_geom
            conflict.parcel_a.validation_status = "VALID"
            conflict.parcel_a.save(update_fields=["geometry", "validation_status"])
            new_geom_wkt = new_geom.wkt
            conflict.status = ConflictStatus.ACCEPTED

        conflict.resolved_at = timezone.now()
        conflict.save(update_fields=["status", "resolved_at"])

        ReviewAction.objects.create(
            conflict=conflict, action=data["action"], reason=data.get("reason", ""),
            performed_by=request.user, previous_geometry=prev_geom_wkt, new_geometry=new_geom_wkt,
        )
        return Response(ConflictDetailSerializer(conflict).data)
