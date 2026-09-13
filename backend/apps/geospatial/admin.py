from django.contrib import admin
from .models import TopologyEdit


@admin.register(TopologyEdit)
class TopologyEditAdmin(admin.ModelAdmin):
    list_display = ("content_type_label", "object_id", "operation", "processing_method", "performed_by", "created_at")
    list_filter = ("operation", "processing_method", "content_type_label")
