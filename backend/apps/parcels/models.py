"""
Canonical, harmonized feature models. These are what the harmonization pipeline
writes to and what the frontend map/reports read from - as opposed to raw
Dataset files, which are the untouched sources.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class ValidationStatus(models.TextChoices):
    UNVALIDATED = "UNVALIDATED", "Unvalidated"
    VALID = "VALID", "Valid"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs Review"
    INVALID = "INVALID", "Invalid"


class Parcel(models.Model):
    parcel_id = models.CharField(max_length=100, db_index=True, blank=True)
    survey_number = models.CharField(max_length=100, blank=True)
    property_reference = models.CharField(max_length=100, blank=True)

    geometry = gis_models.MultiPolygonField(srid=4326, spatial_index=True, null=True, blank=True)
    area = models.FloatField(null=True, blank=True, help_text="sq. meters, computed from geometry")
    land_use = models.CharField(max_length=100, blank=True)

    raw_attributes = models.JSONField(default=dict, blank=True, help_text="Original, unmapped source attributes")

    confidence_score = models.FloatField(default=0)
    validation_status = models.CharField(max_length=20, choices=ValidationStatus.choices, default=ValidationStatus.UNVALIDATED)

    source_datasets = models.ManyToManyField("datasets.Dataset", related_name="parcels", blank=True)

    is_harmonized = models.BooleanField(default=False)
    harmonized_from = models.ManyToManyField(
        "self", symmetrical=False, related_name="harmonized_into", blank=True,
        help_text="Source-specific parcel records that were merged to produce this harmonized parcel."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gh_parcels"
        indexes = [models.Index(fields=["parcel_id"]), models.Index(fields=["validation_status"])]

    def __str__(self):
        return self.parcel_id or f"Parcel#{self.pk}"

    def save(self, *args, **kwargs):
        if self.geometry is not None and not self.pk:
            # transform() requires a saved geometry SRID; area computed on assumption
            # the geometry is already in a projected (metric) CRS at import time.
            pass
        super().save(*args, **kwargs)


class LandRecord(models.Model):
    """Non-spatial harmonized attributes tied 1:1 to a Parcel (ownership refs, land-use class,
    revenue attributes, etc.) - kept separate from geometry per problem statement's guidance
    that ownership is an authoritative attribute, never inferred from imagery."""
    parcel = models.OneToOneField(Parcel, on_delete=models.CASCADE, related_name="land_record")
    ownership_reference = models.CharField(max_length=255, blank=True,
                                            help_text="Reference to authoritative revenue record; NOT inferred by AI.")
    khasra_number = models.CharField(max_length=100, blank=True)
    land_classification = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gh_land_records"


class Building(models.Model):
    footprint_id = models.CharField(max_length=100, blank=True)
    geometry = gis_models.MultiPolygonField(srid=4326, spatial_index=True)
    height_m = models.FloatField(null=True, blank=True)
    floors = models.IntegerField(null=True, blank=True)
    parcel = models.ForeignKey(Parcel, on_delete=models.SET_NULL, null=True, blank=True, related_name="buildings")
    source_dataset = models.ForeignKey("datasets.Dataset", on_delete=models.SET_NULL, null=True, related_name="buildings")
    attributes = models.JSONField(default=dict, blank=True)
    detection_method = models.CharField(
        max_length=20,
        choices=[("SURVEYED", "Surveyed/Digitized"), ("CV_DETECTED", "Computer Vision Detected")],
        default="SURVEYED",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_buildings"


class Road(models.Model):
    road_id = models.CharField(max_length=100, blank=True)
    geometry = gis_models.MultiLineStringField(srid=4326, spatial_index=True)
    road_class = models.CharField(max_length=50, blank=True)
    source_dataset = models.ForeignKey("datasets.Dataset", on_delete=models.SET_NULL, null=True, related_name="roads")
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_roads"


class Utility(models.Model):
    UTILITY_GEOM_CHOICES = [("LINE", "Line"), ("POINT", "Point")]
    utility_type = models.CharField(max_length=50, blank=True, help_text="e.g. WATER, SEWER, POWER, TELECOM")
    geometry = gis_models.GeometryField(srid=4326, spatial_index=True)
    source_dataset = models.ForeignKey("datasets.Dataset", on_delete=models.SET_NULL, null=True, related_name="utilities")
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_utilities"
