"""
Cross-cutting geospatial audit models: every geometry repair/edit is recorded here
(original + modified geometry, operation, reason, timestamp, method) so nothing is
silently overwritten - per the "topology validation" and "audit trail" requirements.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class TopologyEdit(models.Model):
    content_type_label = models.CharField(max_length=50, help_text="e.g. 'parcel', 'building'")
    object_id = models.BigIntegerField()

    original_geometry = gis_models.GeometryField(srid=4326, null=True, blank=True)
    modified_geometry = gis_models.GeometryField(srid=4326, null=True, blank=True)

    operation = models.CharField(max_length=50, help_text="e.g. BUFFER_ZERO, MANUAL_EDIT, SLIVER_REMOVAL")
    reason = models.TextField()
    processing_method = models.CharField(max_length=100, default="AUTOMATIC",
                                          help_text="AUTOMATIC | MANUAL")
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_topology_edits"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.operation} on {self.content_type_label}#{self.object_id}"
