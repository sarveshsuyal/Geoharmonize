import json
from rest_framework import serializers
from apps.datasets.models import Dataset, ProcessingStatus, GeometryKind
from .models import HarmonizationRun, ParcelMatch, AttributeMappingRule


class HarmonizationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = HarmonizationRun
        fields = [
            "id", "status", "progress", "current_step", "dataset_ids",
            "statistics", "error_message", "started_at", "completed_at",
        ]
        read_only_fields = [
            "status", "progress", "current_step", "statistics",
            "error_message", "started_at", "completed_at",
        ]


class StartHarmonizationSerializer(serializers.Serializer):
    dataset_ids = serializers.ListField(child=serializers.IntegerField(), min_length=2)

    def validate_dataset_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("dataset_ids must not contain duplicates.")
        datasets = list(Dataset.objects.filter(id__in=value))
        found_ids = {dataset.id for dataset in datasets}
        missing = sorted(set(value) - found_ids)
        if missing:
            raise serializers.ValidationError(f"Dataset(s) not found: {missing}.")
        not_ready = [
            dataset.name for dataset in datasets
            if dataset.processing_status not in (ProcessingStatus.VALIDATED, ProcessingStatus.PROCESSED)
        ]
        if not_ready:
            raise serializers.ValidationError(
                f"Dataset(s) must be validated before harmonization: {', '.join(not_ready)}."
            )
        if any(dataset.geometry_type == GeometryKind.RASTER for dataset in datasets):
            raise serializers.ValidationError(
                "Raster datasets cannot be used in parcel harmonization yet; select vector datasets."
            )
        if any(not dataset.original_crs for dataset in datasets):
            raise serializers.ValidationError("Every dataset must have a detected or manually specified CRS.")
        return value


class ParcelMatchSerializer(serializers.ModelSerializer):
    source_parcel_ref = serializers.CharField(source="source_parcel.parcel_id", read_only=True)
    target_parcel_ref = serializers.CharField(source="target_parcel.parcel_id", read_only=True)
    source_dataset_name = serializers.SerializerMethodField()
    target_dataset_name = serializers.SerializerMethodField()

    class Meta:
        model = ParcelMatch
        fields = [
            "id", "run", "source_parcel", "source_parcel_ref", "source_dataset_name",
            "target_parcel", "target_parcel_ref", "target_dataset_name",
            "overlap_ratio", "area_similarity", "centroid_distance_m", "shape_similarity",
            "boundary_similarity", "topology_relationship", "attribute_similarity",
            "overall_confidence", "status", "relationship_type", "metrics_detail", "reasons",
            "review_decision", "review_notes", "reviewed_at", "created_at",
        ]

    def get_source_dataset_name(self, obj):
        ds = obj.source_parcel.source_datasets.first()
        return ds.name if ds else ""

    def get_target_dataset_name(self, obj):
        ds = obj.target_parcel.source_datasets.first()
        return ds.name if ds else ""


class ParcelMatchDetailSerializer(ParcelMatchSerializer):
    """Rich serializer for Review Queue with side-by-side attributes and geometry GeoJSON."""
    source_parcel_detail = serializers.SerializerMethodField()
    target_parcel_detail = serializers.SerializerMethodField()
    alternatives = serializers.SerializerMethodField()

    class Meta(ParcelMatchSerializer.Meta):
        fields = ParcelMatchSerializer.Meta.fields + [
            "source_parcel_detail", "target_parcel_detail", "alternatives",
        ]

    def get_source_parcel_detail(self, obj):
        p = obj.source_parcel
        ds = p.source_datasets.first()
        return {
            "id": p.id,
            "parcel_id": p.parcel_id,
            "survey_number": p.survey_number,
            "land_use": p.land_use,
            "area": p.area,
            "dataset_id": ds.id if ds else None,
            "dataset_name": ds.name if ds else "",
            "raw_attributes": p.raw_attributes,
            "geometry_geojson": json.loads(p.geometry.geojson) if p.geometry else None,
        }

    def get_target_parcel_detail(self, obj):
        p = obj.target_parcel
        ds = p.source_datasets.first()
        return {
            "id": p.id,
            "parcel_id": p.parcel_id,
            "survey_number": p.survey_number,
            "land_use": p.land_use,
            "area": p.area,
            "dataset_id": ds.id if ds else None,
            "dataset_name": ds.name if ds else "",
            "raw_attributes": p.raw_attributes,
            "geometry_geojson": json.loads(p.geometry.geojson) if p.geometry else None,
        }

    def get_alternatives(self, obj):
        if not obj.run_id:
            return []
        other_matches = ParcelMatch.objects.filter(
            run_id=obj.run_id, source_parcel_id=obj.source_parcel_id
        ).exclude(id=obj.id).select_related("target_parcel")[:5]

        alts = []
        for om in other_matches:
            tgt = om.target_parcel
            ds = tgt.source_datasets.first()
            alts.append({
                "match_id": om.id,
                "target_parcel_id": tgt.id,
                "target_parcel_ref": tgt.parcel_id,
                "dataset_name": ds.name if ds else "",
                "confidence": om.overall_confidence,
                "overlap_ratio": om.overlap_ratio,
            })
        return alts


class ReviewMatchActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[
        "ACCEPT", "REJECT", "CHOOSE_ALTERNATIVE", "MARK_UNRESOLVED",
        "CONFIRM_SPLIT", "CONFIRM_MERGE",
    ])
    alternative_target_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AttributeMappingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeMappingRule
        fields = ["id", "dataset_type", "source_field_name", "canonical_field_name", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]
