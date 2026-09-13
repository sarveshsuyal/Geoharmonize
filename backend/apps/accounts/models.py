"""
Custom user model with role-based access control.

Roles (per problem statement):
  ADMIN        - full access
  GIS_OFFICER  - upload/process/review/edit proposed changes
  REVIEWER     - review and approve/reject conflicts
  VIEWER       - read-only
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    GIS_OFFICER = "GIS_OFFICER", "GIS Officer"
    REVIEWER = "REVIEWER", "Reviewer"
    VIEWER = "VIEWER", "Viewer"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    organization = models.CharField(max_length=255, blank=True, default="")
    designation = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "gh_users"

    def __str__(self):
        return f"{self.username} ({self.role})"

    # --- permission helpers used across the app instead of scattering role checks ---
    @property
    def can_upload(self):
        return self.role in (Role.ADMIN, Role.GIS_OFFICER)

    @property
    def can_process(self):
        return self.role in (Role.ADMIN, Role.GIS_OFFICER)

    @property
    def can_resolve_conflicts(self):
        return self.role in (Role.ADMIN, Role.GIS_OFFICER, Role.REVIEWER)

    @property
    def can_edit_geometry(self):
        return self.role in (Role.ADMIN, Role.GIS_OFFICER)

    @property
    def is_read_only(self):
        return self.role == Role.VIEWER
