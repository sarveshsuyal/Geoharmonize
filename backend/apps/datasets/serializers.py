from rest_framework import serializers
from .models import Dataset, ProcessingLog


class DatasetSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.username", read_only=True)
    reliability = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "id", "name", "dataset_type", "source", "file", "original_filename",
            "original_crs", "target_crs", "crs_confidence",
            "geometry_type", "feature_count", "bbox",
            "processing_status", "error_message", "metadata", "survey_year",
            "reliability_override", "reliability",
            "uploaded_by", "uploaded_by_name", "created_at", "updated_at",
        ]
        read_only_fields = [
            "original_crs", "target_crs", "crs_confidence", "geometry_type",
            "feature_count", "bbox", "processing_status", "error_message",
            "metadata", "uploaded_by",
        ]

    def get_reliability(self, obj):
        from django.conf import settings
        if obj.reliability_override is not None:
            return obj.reliability_override
        return settings.GEOHARMONIZE["SOURCE_RELIABILITY"].get(obj.dataset_type, 40)

    def create(self, validated_data):
        request = self.context["request"]
        f = validated_data["file"]
        validated_data["original_filename"] = f.name
        validated_data["uploaded_by"] = request.user
        return super().create(validated_data)


class ManualCRSSerializer(serializers.Serializer):
    crs = serializers.CharField(help_text="e.g. EPSG:32644")


class ProcessingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingLog
        fields = ["id", "step", "level", "message", "duration_ms", "created_at"]
