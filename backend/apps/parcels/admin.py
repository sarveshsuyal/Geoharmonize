from django.contrib import admin
from .models import Parcel, LandRecord, Building, Road, Utility


@admin.register(Parcel)
class ParcelAdmin(admin.ModelAdmin):
    list_display = ("parcel_id", "survey_number", "area", "land_use", "confidence_score", "validation_status", "is_harmonized")
    list_filter = ("validation_status", "is_harmonized", "land_use")
    search_fields = ("parcel_id", "survey_number", "property_reference")


@admin.register(LandRecord)
class LandRecordAdmin(admin.ModelAdmin):
    list_display = ("parcel", "ownership_reference", "khasra_number", "land_classification")


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("footprint_id", "parcel", "detection_method", "source_dataset")
    list_filter = ("detection_method",)


@admin.register(Road)
class RoadAdmin(admin.ModelAdmin):
    list_display = ("road_id", "road_class", "source_dataset")


@admin.register(Utility)
class UtilityAdmin(admin.ModelAdmin):
    list_display = ("utility_type", "source_dataset")
    list_filter = ("utility_type",)
