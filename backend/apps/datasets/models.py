"""
Dataset: the raw uploaded source (cadastral map, drone image, municipal GeoJSON, etc.)
before it has been decomposed into harmonized Parcel/Building/Road/Utility features.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


def dataset_upload_path(instance, filename):
    return f"datasets/{instance.dataset_type}/{filename}"


class DatasetType(models.TextChoices):
    CADASTRAL = "CADASTRAL", "Cadastral Map"
    DRONE = "DRONE", "Drone Imagery"
    ORTHO_IMAGE = "ORTHO_IMAGE", "Orthorectified Imagery"
    SATELLITE = "SATELLITE", "Satellite Imagery"
    MUNICIPAL = "MUNICIPAL", "Municipal GIS"
    REVENUE = "REVENUE", "Revenue Records"
    BUILDING = "BUILDING", "Building Footprints"
    ROAD = "ROAD", "Road Network"
    UTILITY = "UTILITY", "Utility Layer"
    GNSS = "GNSS", "GNSS/CORS Survey"
    DSM = "DSM", "Digital Surface Model"
    DTM = "DTM", "Digital Terrain Model"
    OTHER = "OTHER", "Other"


class ProcessingStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    VALIDATING = "VALIDATING", "Validating"
    VALIDATED = "VALIDATED", "Validated"
    PROCESSING = "PROCESSING", "Processing"
    PROCESSED = "PROCESSED", "Processed"
    FAILED = "FAILED", "Failed"
    NEEDS_CRS = "NEEDS_CRS", "CRS Required"


class GeometryKind(models.TextChoices):
    POINT = "POINT", "Point"
    LINESTRING = "LINESTRING", "LineString"
    POLYGON = "POLYGON", "Polygon"
    MULTIPOLYGON = "MULTIPOLYGON", "MultiPolygon"
    RASTER = "RASTER", "Raster"
    UNKNOWN = "UNKNOWN", "Unknown"


class Dataset(models.Model):
    name = models.CharField(max_length=255)
    dataset_type = models.CharField(max_length=30, choices=DatasetType.choices)
    source = models.CharField(max_length=255, help_text="Issuing authority / provider, e.g. 'Revenue Dept 2024'")
    file = models.FileField(upload_to=dataset_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)

    original_crs = models.CharField(max_length=64, blank=True, null=True, help_text="e.g. EPSG:4326")
    target_crs = models.CharField(max_length=64, blank=True, null=True)
    crs_confidence = models.CharField(
        max_length=20,
        choices=[("DETECTED", "Detected"), ("USER_SPECIFIED", "User Specified"), ("UNKNOWN", "Unknown")],
        default="UNKNOWN",
    )

    geometry_type = models.CharField(max_length=20, choices=GeometryKind.choices, default=GeometryKind.UNKNOWN)
    feature_count = models.IntegerField(null=True, blank=True)
    bbox = models.JSONField(null=True, blank=True, help_text="[minx, miny, maxx, maxy] in original CRS")

    processing_status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.UPLOADED)
    error_message = models.TextField(blank=True, default="")

    metadata = models.JSONField(default=dict, blank=True, help_text="Raw file metadata (driver, layers, band info, EXIF, etc.)")
    survey_year = models.IntegerField(null=True, blank=True)

    reliability_override = models.IntegerField(
        null=True, blank=True,
        help_text="0-100. If unset, falls back to GEOHARMONIZE.SOURCE_RELIABILITY[dataset_type]."
    )

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="datasets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gh_datasets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.dataset_type})"


class ProcessingLog(models.Model):
    """Append-only log of every processing step, for auditability & debugging."""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="logs", null=True, blank=True)
    harmonization_run = models.ForeignKey(
        "harmonization.HarmonizationRun", on_delete=models.CASCADE, related_name="logs", null=True, blank=True
    )
    step = models.CharField(max_length=100)
    level = models.CharField(max_length=10, choices=[("INFO", "Info"), ("WARNING", "Warning"), ("ERROR", "Error")], default="INFO")
    message = models.TextField()
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_processing_logs"
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.level}] {self.step}: {self.message[:60]}"
