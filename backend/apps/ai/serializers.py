from rest_framework import serializers
from .models import AIAnalysisRun, AIAnalysisFeature, AIPlanningRecommendation


class AIAnalysisRequestSerializer(serializers.Serializer):
    aoi = serializers.JSONField(help_text="GeoJSON Polygon geometry or coordinate ring")
    bounds = serializers.ListField(
        child=serializers.FloatField(), required=False, allow_null=True,
        help_text="[west, south, east, north]"
    )


class AIAnalysisRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysisRun
        fields = [
            "id",
            "aoi_geometry",
            "aoi_bounds",
            "area_m2",
            "source_imagery_type",
            "status",
            "method_category",
            "model_name",
            "model_version",
            "is_ml_model",
            "confidence_score",
            "summary_statistics",
            "features_geojson",
            "recommendations_geojson",
            "error_message",
            "created_at",
            "completed_at",
        ]
