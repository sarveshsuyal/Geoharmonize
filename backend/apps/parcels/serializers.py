from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Parcel, LandRecord, Building, Road, Utility


class LandRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandRecord
        fields = ["ownership_reference", "khasra_number", "land_classification", "remarks"]


class ParcelGeoSerializer(GeoFeatureModelSerializer):
    """Used for the map layer - returns GeoJSON FeatureCollection."""
    confidence_band = serializers.SerializerMethodField()

    class Meta:
        model = Parcel
        geo_field = "geometry"
        fields = ["id", "parcel_id", "survey_number", "area", "land_use",
                  "confidence_score", "confidence_band", "validation_status", "is_harmonized"]

    def get_confidence_band(self, obj):
        from apps.harmonization.services.confidence_service import ConfidenceService
        return ConfidenceService().classify(obj.confidence_score)


class ParcelDetailSerializer(serializers.ModelSerializer):
    """Used for the parcel-details side panel - includes provenance, land record, conflicts."""
    land_record = LandRecordSerializer(read_only=True)
    source_dataset_names = serializers.SerializerMethodField()
    conflict_count = serializers.SerializerMethodField()
    confidence_band = serializers.SerializerMethodField()
    geometry_geojson = serializers.SerializerMethodField()

    class Meta:
        model = Parcel
        fields = [
            "id", "parcel_id", "survey_number", "property_reference", "area", "land_use",
            "confidence_score", "confidence_band", "validation_status", "is_harmonized",
            "raw_attributes", "land_record", "source_dataset_names", "conflict_count",
            "geometry_geojson", "created_at", "updated_at",
        ]

    def get_source_dataset_names(self, obj):
        return list(obj.source_datasets.values_list("name", flat=True))

    def get_conflict_count(self, obj):
        return obj.conflicts_a.exclude(status="ACCEPTED").count() + obj.conflicts_b.exclude(status="ACCEPTED").count() \
            if hasattr(obj, "conflicts_a") else 0

    def get_confidence_band(self, obj):
        from apps.harmonization.services.confidence_service import ConfidenceService
        return ConfidenceService().classify(obj.confidence_score)

    def get_geometry_geojson(self, obj):
        import json
        return json.loads(obj.geometry.geojson) if obj.geometry else None


class BuildingGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Building
        geo_field = "geometry"
        fields = ["id", "footprint_id", "height_m", "floors", "detection_method"]


class RoadGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Road
        geo_field = "geometry"
        fields = ["id", "road_id", "road_class"]


class UtilityGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Utility
        geo_field = "geometry"
        fields = ["id", "utility_type"]
