from rest_framework import serializers
from .models import Conflict, ReviewAction


class ReviewActionSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source="performed_by.username", read_only=True)

    class Meta:
        model = ReviewAction
        fields = ["id", "action", "reason", "performed_by", "performed_by_name",
                  "previous_geometry", "new_geometry", "created_at"]
        read_only_fields = ["performed_by"]


class ConflictListSerializer(serializers.ModelSerializer):
    parcel_a_ref = serializers.CharField(source="parcel_a.parcel_id", read_only=True)
    parcel_b_ref = serializers.CharField(source="parcel_b.parcel_id", read_only=True)
    dataset_a_name = serializers.CharField(source="dataset_a.name", read_only=True)
    dataset_b_name = serializers.CharField(source="dataset_b.name", read_only=True)

    class Meta:
        model = Conflict
        fields = ["id", "conflict_type", "severity", "parcel_a", "parcel_a_ref", "parcel_b", "parcel_b_ref",
                  "dataset_a_name", "dataset_b_name", "description", "measured_difference",
                  "confidence", "status", "created_at", "resolved_at"]


class ConflictDetailSerializer(ConflictListSerializer):
    review_actions = ReviewActionSerializer(many=True, read_only=True)
    parcel_a_geojson = serializers.SerializerMethodField()
    parcel_b_geojson = serializers.SerializerMethodField()

    class Meta(ConflictListSerializer.Meta):
        fields = ConflictListSerializer.Meta.fields + ["suggested_resolution", "review_actions",
                                                         "parcel_a_geojson", "parcel_b_geojson"]

    def get_parcel_a_geojson(self, obj):
        import json
        return json.loads(obj.parcel_a.geometry.geojson) if obj.parcel_a and obj.parcel_a.geometry else None

    def get_parcel_b_geojson(self, obj):
        import json
        return json.loads(obj.parcel_b.geometry.geojson) if obj.parcel_b and obj.parcel_b.geometry else None


class ResolveConflictSerializer(serializers.Serializer):
    ACTION_CHOICES = ["ACCEPT", "KEEP_EXISTING", "EDIT_GEOMETRY", "REJECT", "FIELD_VERIFICATION"]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
    new_geometry_geojson = serializers.JSONField(required=False)
