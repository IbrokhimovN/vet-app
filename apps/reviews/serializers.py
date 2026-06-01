"""Izoh serializerlari (ARCHITECTURE.md 4.2)."""
from rest_framework import serializers

from apps.requests.models import CallRequest, CallStatus

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """O'qish — vet sahifasida izohlar ro'yxati."""

    client_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "client_name", "stars", "comment", "created_at")

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.first_name or "Mijoz"


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Yozish — mijoz yakunlangan chaqiruvga izoh qoldiradi."""

    class Meta:
        model = Review
        fields = ("id", "request", "stars", "comment")
        read_only_fields = ("id",)

    def validate_request(self, call):
        user = self.context["request"].user
        if call.client_id != user.id:
            raise serializers.ValidationError("Bu chaqiruv sizga tegishli emas.")
        if call.status != CallStatus.COMPLETED:
            raise serializers.ValidationError(
                "Faqat yakunlangan chaqiruvga izoh qoldirish mumkin."
            )
        if Review.objects.filter(request=call).exists():
            raise serializers.ValidationError("Bu chaqiruvga allaqachon izoh qoldirilgan.")
        return call

    def create(self, validated_data):
        call = validated_data["request"]
        return Review.objects.create(
            client=call.client, vet=call.vet, **validated_data
        )
