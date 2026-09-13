from django.db import models


class ChangeDetectionRun(models.Model):
    dataset_before = models.ForeignKey("datasets.Dataset", on_delete=models.CASCADE, related_name="change_runs_before")
    dataset_after = models.ForeignKey("datasets.Dataset", on_delete=models.CASCADE, related_name="change_runs_after")
    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("COMPLETED", "Completed"), ("FAILED", "Failed")], default="PENDING")
    statistics = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_change_detection_runs"
        ordering = ["-created_at"]


class ChangeFeature(models.Model):
    CHANGE_TYPES = [("ADDED", "Added"), ("REMOVED", "Removed"), ("MODIFIED", "Modified"), ("UNCHANGED", "Unchanged")]
    run = models.ForeignKey(ChangeDetectionRun, on_delete=models.CASCADE, related_name="features")
    feature_kind = models.CharField(max_length=20, help_text="PARCEL | BUILDING | ROAD | UTILITY | LAND_USE")
    change_type = models.CharField(max_length=10, choices=CHANGE_TYPES)
    geometry_before = models.TextField(null=True, blank=True, help_text="WKT")
    geometry_after = models.TextField(null=True, blank=True, help_text="WKT")
    iou = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_change_features"
