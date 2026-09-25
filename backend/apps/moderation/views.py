"""Shikoyat view'lari — foydalanuvchi boshqasidan shikoyat qiladi."""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .serializers import ReportCreateSerializer


class ReportCreateView(generics.CreateAPIView):
    """POST /reports/ — reported_user, reason, comment (+ ixtiyoriy chaqiruv/so'rov)."""

    serializer_class = ReportCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)
