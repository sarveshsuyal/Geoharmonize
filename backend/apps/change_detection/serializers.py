from rest_framework import serializers
from .models import ChangeDetectionRun, ChangeFeature


class ChangeFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeFeature
        fields = ["id", "feature_kind", "change_type", "geometry_before", "geometry_after", "iou"]


class ChangeDetectionRunSerializer(serializers.ModelSerializer):
    features = ChangeFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = ChangeDetectionRun
        fields = ["id", "dataset_before", "dataset_after", "status", "statistics", "error_message", "created_at", "features"]
        read_only_fields = ["status", "statistics", "error_message"]


class RunChangeDetectionSerializer(serializers.Serializer):
    dataset_before_id = serializers.IntegerField()
    dataset_after_id = serializers.IntegerField()
