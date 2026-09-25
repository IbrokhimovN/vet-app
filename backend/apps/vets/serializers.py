"""vets serializerlari (ARCHITECTURE.md 6.2, 6.3)."""
from rest_framework import serializers

from .models import Service, Specialization, VetProfile


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ("id", "name", "slug", "icon")


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("id", "title", "price", "duration_min")


class VetListSerializer(serializers.ModelSerializer):
    """Qidiruv ro'yxatidagi qisqa vet kartasi (mijoz tomoni)."""

    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    photo = serializers.SerializerMethodField()
    specializations = SpecializationSerializer(many=True, read_only=True)
    # View hisoblab beradi (Haversine); modelda yo'q.
    distance_km = serializers.FloatField(read_only=True, default=None)
    min_price = serializers.SerializerMethodField()

    class Meta:
        model = VetProfile
        fields = (
            "id",
            "full_name",
            "photo",
            "clinic_name",
            "city",
            "district",
            "experience_years",
            "rating_avg",
            "rating_count",
            "is_verified",
            "is_top",
            "is_available",
            "accepts_home_visit",
            "accepts_online",
            "specializations",
            "distance_km",
            "min_price",
            "lat",
            "lng",
        )

    def get_min_price(self, obj):
        prices = [s.price for s in obj.services.all()]
        return min(prices) if prices else None

    def get_photo(self, obj):
        if obj.user.photo:
            return obj.user.photo.url
        return obj.user.photo_url or None


class VetDetailSerializer(VetListSerializer):
    """Vet sahifasi — to'liq ma'lumot + xizmatlar (mijoz tomoni)."""

    services = ServiceSerializer(many=True, read_only=True)

    class Meta(VetListSerializer.Meta):
        fields = VetListSerializer.Meta.fields + (
            "bio",
            "address",
            "services",
        )


class VetProfileSerializer(serializers.ModelSerializer):
    """Vet o'z profilini ko'radi/tahrirlaydi (`/api/v1/vets/me/`)."""

    services = ServiceSerializer(many=True, read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    # Yozishda mutaxassisliklar id ro'yxati orqali beriladi.
    specialization_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Specialization.objects.all(),
        source="specializations",
        write_only=True,
        required=False,
    )
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = VetProfile
        fields = (
            "id",
            "full_name",
            "bio",
            "experience_years",
            "clinic_name",
            "lat",
            "lng",
            "address",
            "city",
            "district",
            "is_verified",
            "is_available",
            "license_document",
            "rating_avg",
            "rating_count",
            "specializations",
            "specialization_ids",
            "accepts_home_visit",
            "accepts_online",
            "services",
        )
        # Bu maydonlarni vet o'zi o'zgartira olmaydi (faqat admin/tizim).
        read_only_fields = ("is_verified", "rating_avg", "rating_count")
