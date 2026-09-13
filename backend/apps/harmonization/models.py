from django.conf import settings
from django.db import models


class RunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class HarmonizationRun(models.Model):
    status = models.CharField(max_length=20, choices=RunStatus.choices, default=RunStatus.PENDING)
    progress = models.IntegerField(default=0, help_text="0-100")
    current_step = models.CharField(max_length=100, blank=True)
    dataset_ids = models.JSONField(default=list, help_text="Datasets included in this run")
    statistics = models.JSONField(default=dict, blank=True,
                                   help_text="matched/unmatched/conflict counts etc., computed - never hard-coded")
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gh_harmonization_runs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Run#{self.pk} [{self.status}] {self.progress}%"


class MatchStatus(models.TextChoices):
    MATCH = "MATCH", "Match"
    REVIEW = "REVIEW", "Review Required"
    NO_MATCH = "NO_MATCH", "No Match"
    UNMATCHED = "UNMATCHED", "Unmatched"
    SPLIT = "SPLIT", "Split (1:N)"
    MERGE = "MERGE", "Merge (N:1)"
    MATCHED = "MATCHED", "Matched"
    CANDIDATE = "CANDIDATE", "Candidate"
    REJECTED = "REJECTED", "Rejected"


class ParcelMatch(models.Model):
    """
    Records a proposed correspondence between a parcel feature in one dataset
    and a parcel feature in another. Scores are always computed from real
    geometry/attribute measurements.
    """
    run = models.ForeignKey(HarmonizationRun, on_delete=models.CASCADE, related_name="matches", null=True, blank=True)

    source_parcel = models.ForeignKey("parcels.Parcel", on_delete=models.CASCADE, related_name="matches_as_source")
    target_parcel = models.ForeignKey("parcels.Parcel", on_delete=models.CASCADE, related_name="matches_as_target")

    overlap_ratio = models.FloatField(help_text="Intersection-over-Union, 0-1")
    area_similarity = models.FloatField(help_text="0-1")
    centroid_distance_m = models.FloatField()
    shape_similarity = models.FloatField(help_text="0-1, boundary/compactness comparison")
    boundary_similarity = models.FloatField(default=0.0, help_text="0-1 boundary proximity / Hausdorff score")
    topology_relationship = models.CharField(max_length=50, blank=True, default="OVERLAPS")
    attribute_similarity = models.FloatField(default=0.0, help_text="0-1 attribute similarity")

    overall_confidence = models.FloatField(help_text="0-100, computed by ConfidenceService")
    status = models.CharField(max_length=20, choices=MatchStatus.choices, default=MatchStatus.REVIEW)
    relationship_type = models.CharField(
        max_length=30,
        choices=[
            ("ONE_TO_ONE", "1:1 Match"),
            ("SPLIT", "1:N Split"),
            ("MERGE", "N:1 Merge"),
            ("ONE_TO_MANY", "1:N Relationship"),
            ("MANY_TO_ONE", "N:1 Relationship"),
            ("UNRESOLVED", "Unresolved"),
        ],
        default="ONE_TO_ONE",
    )

    metrics_detail = models.JSONField(default=dict, blank=True, help_text="Detailed explainable metrics breakdown")
    reasons = models.JSONField(default=list, blank=True, help_text="Explainable reasons list")

    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_decision = models.CharField(max_length=50, blank=True, default="")
    review_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_parcel_matches"
        unique_together = ("source_parcel", "target_parcel")

    def __str__(self):
        return f"{self.source_parcel_id} <-> {self.target_parcel_id} [{self.relationship_type}] ({self.overall_confidence:.1f}%)"


class ParcelMatchReviewAction(models.Model):
    """Immutable audit record for every human decision on a match."""
    match = models.ForeignKey(ParcelMatch, on_delete=models.CASCADE, related_name="review_actions")
    action = models.CharField(max_length=50)
    reason = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    previous_status = models.CharField(max_length=20, blank=True)
    resulting_status = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_parcel_match_review_actions"
        ordering = ["-created_at"]



class AttributeMappingRule(models.Model):
    """
    Officer-maintained mapping from a source dataset's raw field name to the
    canonical ParcelRecord schema, e.g. 'khasra_no' -> 'survey_number'.
    Seeded with sensible defaults but always editable (see attribute_mapping.py).
    """
    dataset_type = models.CharField(max_length=30)
    source_field_name = models.CharField(max_length=100)
    canonical_field_name = models.CharField(max_length=100, choices=[
        ("parcel_id", "parcel_id"),
        ("survey_number", "survey_number"),
        ("property_id", "property_id"),
        ("area", "area"),
        ("land_use", "land_use"),
        ("ownership_reference", "ownership_reference"),
    ])
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_attribute_mapping_rules"
        unique_together = ("dataset_type", "source_field_name")

    def __str__(self):
        return f"{self.dataset_type}.{self.source_field_name} -> {self.canonical_field_name}"
