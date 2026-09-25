"""requests uchun ruxsatlar."""
from rest_framework.permissions import BasePermission


class IsClient(BasePermission):
    message = "Bu amal faqat mijozlar uchun."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_client)


class IsVet(BasePermission):
    message = "Bu amal faqat veterinarlar uchun."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_vet)
