from django.db import models


class AIAnalysisRun(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    aoi_geometry = models.JSONField(help_text="GeoJSON Polygon geometry of the Area of Interest")
    aoi_bounds = models.JSONField(null=True, blank=True, help_text="[west, south, east, north]")
    area_m2 = models.FloatField(default=0.0, help_text="Analyzed area in square meters")

    source_imagery_type = models.CharField(max_length=50, default="SATELLITE_TILES")
    source_dataset = models.ForeignKey(
        "datasets.Dataset", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_analyses"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    method_category = models.CharField(max_length=50, default="COMPUTER_VISION_HEURISTIC")
    model_name = models.CharField(max_length=100, default="GeoHarmonize CV & Spectral Classifier")
    model_version = models.CharField(max_length=20, default="1.0-prototype")
    is_ml_model = models.BooleanField(default=False, help_text="False for classical CV/spectral heuristic")

    confidence_score = models.FloatField(default=0.0)
    summary_statistics = models.JSONField(default=dict, blank=True)
    features_geojson = models.JSONField(default=dict, blank=True)
    recommendations_geojson = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gh_ai_analysis_runs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"AIAnalysisRun#{self.pk} ({self.status}) - {self.area_m2:.1f} m²"


class AIAnalysisFeature(models.Model):
    FEATURE_TYPES = [
        ("BUILT_UP", "Built-up / Occupied"),
        ("BARE_LAND", "Bare / Vacant Land"),
        ("AGRICULTURE", "Agriculture / Cropland"),
        ("VEGETATION", "Vegetation / Green Area"),
        ("WATER", "Water Body"),
        ("ROAD", "Road / Infrastructure"),
        ("UNKNOWN", "Unknown"),
    ]

    analysis_run = models.ForeignKey(AIAnalysisRun, on_delete=models.CASCADE, related_name="features")
    feature_type = models.CharField(max_length=30, choices=FEATURE_TYPES)
    geometry_wkt = models.TextField(help_text="WKT polygon geometry")
    area_m2 = models.FloatField(default=0.0)
    confidence = models.FloatField(default=0.0)
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_ai_analysis_features"


class AIPlanningRecommendation(models.Model):
    REC_TYPES = [
        ("AGRICULTURE", "Agriculture Candidate"),
        ("CONSTRUCTION", "Construction Candidate"),
        ("NOT_RECOMMENDED", "Not Recommended / Low Confidence"),
    ]

    analysis_run = models.ForeignKey(AIAnalysisRun, on_delete=models.CASCADE, related_name="recommendations")
    recommendation_type = models.CharField(max_length=30, choices=REC_TYPES)
    geometry_wkt = models.TextField(help_text="WKT candidate polygon geometry")
    suitability_score = models.FloatField(default=0.0, help_text="0-100")
    confidence = models.FloatField(default=0.0, help_text="0-100")
    area_m2 = models.FloatField(default=0.0)
    reasons = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gh_ai_planning_recommendations"
