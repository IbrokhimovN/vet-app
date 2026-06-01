"""Bildirishnoma serializerlari (ilova ichidagi lenta uchun)."""
from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id", "kind", "kind_display", "title", "body",
            "is_read", "is_sent", "created_at",
            "call_request", "service_request", "offer",
        )
        read_only_fields = fields
