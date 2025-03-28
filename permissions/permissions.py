from rest_framework import permissions

class IsVerified(permissions.BasePermission):
    """Allows access only to verified users."""
    def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_verified

class IsAdministrator(permissions.BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_administrator

class IsModerator(permissions.BasePermission):
    """Allows access only to moderators."""
    def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_moderator

class IsCommunityManager(permissions.BasePermission):
    """Allows access only to community managers."""
    def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_community_manager

class IsClient(permissions.BasePermission):
    """Allows access only to clients."""
    def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_client
