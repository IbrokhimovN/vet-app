"""Izoh serializerlari (ARCHITECTURE.md 4.2)."""
from rest_framework import serializers

from apps.requests.models import CallStatus, ServiceStatus

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """O'qish — vet sahifasida izohlar ro'yxati."""

    client_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "client_name", "stars", "comment", "created_at")

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.first_name or "Mijoz"


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """Yangilash — mijoz o'zi yozgan izohini tahrirlaydi (faqat baho/matn)."""

    class Meta:
        model = Review
        fields = ("id", "stars", "comment")
        read_only_fields = ("id",)


class ReviewCreateSerializer(serializers.ModelSerializer):
    """
    Yozish — mijoz yakunlangan chaqiruvga (`request`) YOKI yakunlangan ochiq
    so'rovga (`service_request`) izoh qoldiradi. Aynan bittasi berilishi kerak.
    """

    class Meta:
        model = Review
        fields = ("id", "request", "service_request", "stars", "comment")
        read_only_fields = ("id",)
        extra_kwargs = {
            "request": {"required": False, "allow_null": True},
            "service_request": {"required": False, "allow_null": True},
        }

    def validate(self, data):
        call = data.get("request")
        sr = data.get("service_request")
        if bool(call) == bool(sr):
            raise serializers.ValidationError(
                "Faqat bitta manba ko'rsatilishi kerak: chaqiruv yoki ochiq so'rov."
            )
        user = self.context["request"].user
        if call:
            if call.client_id != user.id:
                raise serializers.ValidationError("Bu chaqiruv sizga tegishli emas.")
            if call.status != CallStatus.COMPLETED:
                raise serializers.ValidationError(
                    "Faqat yakunlangan chaqiruvga izoh qoldirish mumkin."
                )
            if Review.objects.filter(request=call).exists():
                raise serializers.ValidationError("Bu chaqiruvga allaqachon izoh qoldirilgan.")
        else:
            if sr.client_id != user.id:
                raise serializers.ValidationError("Bu so'rov sizga tegishli emas.")
            if sr.status != ServiceStatus.COMPLETED:
                raise serializers.ValidationError(
                    "Faqat yakunlangan so'rovga izoh qoldirish mumkin."
                )
            if not sr.assigned_offer_id:
                raise serializers.ValidationError("Bu so'rovga vet tayinlanmagan.")
            if Review.objects.filter(service_request=sr).exists():
                raise serializers.ValidationError("Bu so'rovga allaqachon izoh qoldirilgan.")
        return data

    def create(self, validated_data):
        call = validated_data.get("request")
        if call:
            return Review.objects.create(
                client=call.client, vet=call.vet, **validated_data
            )
        sr = validated_data["service_request"]
        return Review.objects.create(
            client=sr.client, vet=sr.assigned_offer.vet, **validated_data
        )
