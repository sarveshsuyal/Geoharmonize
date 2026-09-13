"""
Map-bounds-filtered GeoJSON endpoints. The frontend map never requests the
whole table - it always passes bbox params so only features in view are sent.
"""
from django.contrib.gis.geos import Polygon
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


class BBoxFilterMixin:
    def get_bbox_polygon(self, request):
        bbox = request.query_params.get("bbox")  # "minx,miny,maxx,maxy"
        if not bbox:
            return None
        try:
            minx, miny, maxx, maxy = [float(v) for v in bbox.split(",")]
        except ValueError:
            return None
        return Polygon.from_bbox((minx, miny, maxx, maxy))


class LayersSummaryView(APIView):
    """GET /api/geospatial/layers/ -> which layers currently have data, for the map layer toggle panel."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.parcels.models import Parcel, Building, Road, Utility
        from apps.conflicts.models import Conflict
        return Response({
            "parcels": Parcel.objects.count(),
            "buildings": Building.objects.count(),
            "roads": Road.objects.count(),
            "utilities": Utility.objects.count(),
            "conflicts": Conflict.objects.exclude(status="RESOLVED").count(),
        })
