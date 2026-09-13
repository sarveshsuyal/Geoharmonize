from django.contrib import admin
from .models import HarmonizationRun, ParcelMatch, AttributeMappingRule


@admin.register(HarmonizationRun)
class HarmonizationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "progress", "current_step", "started_at", "completed_at")
    list_filter = ("status",)
    readonly_fields = ("statistics",)


@admin.register(ParcelMatch)
class ParcelMatchAdmin(admin.ModelAdmin):
    list_display = ("source_parcel", "target_parcel", "overall_confidence", "status", "created_at")
    list_filter = ("status",)


@admin.register(AttributeMappingRule)
class AttributeMappingRuleAdmin(admin.ModelAdmin):
    list_display = ("dataset_type", "source_field_name", "canonical_field_name", "created_by")
    list_filter = ("dataset_type",)
