from django.contrib import admin
from .models import ChangeDetectionRun, ChangeFeature

@admin.register(ChangeDetectionRun)
class ChangeDetectionRunAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset_before", "dataset_after", "status", "created_at")

@admin.register(ChangeFeature)
class ChangeFeatureAdmin(admin.ModelAdmin):
    list_display = ("run", "feature_kind", "change_type", "iou")
    list_filter = ("change_type", "feature_kind")
