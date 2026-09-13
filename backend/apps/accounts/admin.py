from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class GeoHarmonizeUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "organization", "is_active", "date_joined")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("username", "email", "organization")
    fieldsets = UserAdmin.fieldsets + (
        ("GeoHarmonize", {"fields": ("role", "organization", "designation")}),
    )
