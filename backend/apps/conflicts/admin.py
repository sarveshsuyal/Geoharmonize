from django.contrib import admin
from .models import Conflict, ReviewAction


@admin.register(Conflict)
class ConflictAdmin(admin.ModelAdmin):
    list_display = ("id", "conflict_type", "severity", "status", "confidence", "created_at")
    list_filter = ("conflict_type", "severity", "status")
    readonly_fields = ("measured_difference",)


@admin.register(ReviewAction)
class ReviewActionAdmin(admin.ModelAdmin):
    list_display = ("conflict", "action", "performed_by", "created_at")
    list_filter = ("action",)
