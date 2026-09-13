from django.conf import settings
from django.db import models


class ConflictType(models.TextChoices):
    BOUNDARY_DISCREPANCY = "BOUNDARY_DISCREPANCY", "Boundary Discrepancy"
    AREA_MISMATCH = "AREA_MISMATCH", "Area Mismatch"
    ATTRIBUTE_MISMATCH = "ATTRIBUTE_MISMATCH", "Attribute Mismatch (e.g. land use)"
    BUILDING_CROSSES_PARCEL = "BUILDING_CROSSES_PARCEL", "Building Crosses Parcel Boundary"
    UTILITY_CROSSES_PARCEL = "UTILITY_CROSSES_PARCEL", "Utility Crosses Parcel"
    DUPLICATE_PARCEL = "DUPLICATE_PARCEL", "Duplicate Parcel Record"
    MISSING_IN_SOURCE = "MISSING_IN_SOURCE", "Parcel Missing In One Source"
    TOPOLOGY_ERROR = "TOPOLOGY_ERROR", "Geometry/Topology Error"


class Severity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class ConflictStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    AUTO_RESOLVED = "AUTO_RESOLVED", "Auto Resolved"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    FIELD_VERIFICATION = "FIELD_VERIFICATION", "Field Verification Required"


class Conflict(models.Model):
    conflict_type = models.CharField(max_length=30, choices=ConflictType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices)

    dataset_a = models.ForeignKey("datasets.Dataset", on_delete=models.SET_NULL, null=True, blank=True, related_name="conflicts_a")
    dataset_b = models.ForeignKey("datasets.Dataset", on_delete=models.SET_NULL, null=True, blank=True, related_name="conflicts_b")

    parcel_a = models.ForeignKey("parcels.Parcel", on_delete=models.CASCADE, null=True, blank=True, related_name="conflicts_a")
    parcel_b = models.ForeignKey("parcels.Parcel", on_delete=models.CASCADE, null=True, blank=True, related_name="conflicts_b")
    affected_building = models.ForeignKey("parcels.Building", on_delete=models.CASCADE, null=True, blank=True)
    affected_utility = models.ForeignKey("parcels.Utility", on_delete=models.CASCADE, null=True, blank=True)

    description = models.TextField()
    measured_difference = models.JSONField(default=dict, help_text="e.g. {'boundary_diff_m': 1.24} or {'area_diff_pct': 8.2}")
    suggested_resolution = models.TextField(blank=True)
    confidence = models.FloatField(default=0)

    run = models.ForeignKey("harmonization.HarmonizationRun", on_delete=models.SET_NULL, null=True, blank=True, related_name="conflicts")

    status = models.CharField(max_length=20, choices=ConflictStatus.choices, default=ConflictStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gh_conflicts"
        ordering = ["-severity", "-created_at"]

    def __str__(self):
        return f"Conflict#{self.pk} [{self.conflict_type}] {self.severity}"


class ReviewAction(models.Model):
    """Every human decision on a conflict, permanently recorded (audit trail)."""
    ACTIONS = [
        ("ACCEPT", "Accept"), ("KEEP_EXISTING", "Keep Existing"),
        ("EDIT_GEOMETRY", "Edit Geometry"), ("REJECT", "Reject"),
        ("FIELD_VERIFICATION", "Field Verification"),
    ]
    conflict = models.ForeignKey(Conflict, on_delete=models.CASCADE, related_name="review_actions")
    action = models.CharField(max_length=30, choices=ACTIONS)
    reason = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    previous_geometry = models.TextField(blank=True, null=True, help_text="WKT snapshot before this action, if geometry changed")
    new_geometry = models.TextField(blank=True, null=True, help_text="WKT snapshot after this action, if geometry changed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_review_actions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on Conflict#{self.conflict_id} by {self.performed_by}"
