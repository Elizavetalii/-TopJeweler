from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admins to access certain views.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsManagerUser(permissions.BasePermission):
    """
    Custom permission to only allow managers to access certain views.
    """

    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Managers').exists()


class IsClientUser(permissions.BasePermission):
    """
    Custom permission to only allow clients to access certain views.
    """

    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Clients').exists()