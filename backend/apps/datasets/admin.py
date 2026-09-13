from django.contrib import admin
from .models import Dataset, ProcessingLog


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "dataset_type", "source", "processing_status", "geometry_type",
                     "feature_count", "original_crs", "created_at")
    list_filter = ("dataset_type", "processing_status", "geometry_type")
    search_fields = ("name", "source")
    readonly_fields = ("metadata", "bbox", "created_at", "updated_at")


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ("step", "level", "dataset", "harmonization_run", "created_at")
    list_filter = ("level", "step")
    search_fields = ("message",)
