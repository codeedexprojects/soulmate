from rest_framework.permissions import BasePermission

class IsManagerExecutive(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'manager_executive'

class IsManagerUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'manager_user'