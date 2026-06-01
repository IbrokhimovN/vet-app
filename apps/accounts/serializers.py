"""accounts serializerlari."""
from rest_framework import serializers

from .models import User


class TelegramAuthSerializer(serializers.Serializer):
    """Kirish so'rovi: initData + qaysi Mini App."""

    init_data = serializers.CharField(help_text="Telegram WebApp initData satri")
    app = serializers.ChoiceField(
        choices=["client", "vet"], help_text="Qaysi Mini App orqali kirilgani"
    )


class UserSerializer(serializers.ModelSerializer):
    """Foydalanuvchi ma'lumotlari (javoblarda)."""

    class Meta:
        model = User
        fields = (
            "id",
            "telegram_id",
            "role",
            "first_name",
            "last_name",
            "username",
            "phone",
            "language",
            "photo_url",
        )
        read_only_fields = ("id", "telegram_id", "role")
