"""
Reusable DRF permission classes mapping GeoHarmonize roles to actions.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "ADMIN")


class CanUploadOrProcess(BasePermission):
    """Allows GET for everyone authenticated; write actions require GIS_OFFICER/ADMIN."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.can_upload


class CanResolveConflicts(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.can_resolve_conflicts


class ReadOnlyForViewer(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_read_only:
            return request.method in SAFE_METHODS
        return True
