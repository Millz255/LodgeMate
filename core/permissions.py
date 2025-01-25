# core/permissions.py

from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'

class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['admin', 'staff']

class IsGuest(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'guest'
