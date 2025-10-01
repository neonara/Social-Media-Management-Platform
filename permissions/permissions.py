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
    

class IsAssignedToPost(permissions.BasePermission):
    """
    Custom permission to allow only assigned users to edit a post.
    """

    def has_object_permission(self, request, view, obj):
        # Ensure the object is a Post and the user is assigned to it
        return obj.is_user_assigned(request.user)

class IsModeratorOrCM(permissions.BasePermission):
    """
    Custom permission to allow only Moderators or Community Managers to access certain views.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_moderator or request.user.is_community_manager
        )

class IsModeratorOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow only Moderators or Administrators to access certain views.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_moderator or request.user.is_administrator
        )

class IsModeratorOrCMOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow Moderators, Community Managers, or Administrators to access certain views.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_moderator or 
            request.user.is_community_manager or 
            request.user.is_administrator or
            request.user.is_superadministrator
        )

class IsAssignedToPostOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow assigned users or administrators to edit a post.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access any post, otherwise check if user is assigned
        return (request.user.is_administrator or 
                obj.is_user_assigned(request.user))
