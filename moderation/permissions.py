from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "Réservé aux administrateurs."

    def has_permission(self, request, view):
        u = getattr(getattr(request, "user", None), "user", None)
        return bool(u and getattr(u, "role", "") == "admin")