"""vets uchun ruxsatlar."""
from rest_framework.permissions import BasePermission


class IsVet(BasePermission):
    """Faqat roli 'vet' bo'lgan foydalanuvchilarga ruxsat."""

    message = "Bu amal faqat veterinarlar uchun."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_vet)
