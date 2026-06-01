"""requests serializerlari (ARCHITECTURE.md 6.2, 6.3)."""
from rest_framework import serializers

from apps.pets.models import Pet
from apps.vets.models import Specialization, VetProfile

from .models import CallRequest, Offer, OfferStatus, ServiceRequest


class VetMiniSerializer(serializers.ModelSerializer):
    """Javoblarda vet haqida qisqa ma'lumot."""

    full_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = VetProfile
        fields = ("id", "full_name", "clinic_name", "rating_avg", "city")


class PetMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ("id", "name", "species")


# ------------------------- REJIM A: CallRequest -------------------------

class CallRequestSerializer(serializers.ModelSerializer):
    """To'g'ridan chaqiruv — yaratish va o'qish."""

    vet = serializers.PrimaryKeyRelatedField(queryset=VetProfile.objects.all())
    vet_info = VetMiniSerializer(source="vet", read_only=True)
    pet = serializers.PrimaryKeyRelatedField(
        queryset=Pet.objects.all(), required=False, allow_null=True
    )
    pet_info = PetMiniSerializer(source="pet", read_only=True)
    has_review = serializers.SerializerMethodField()

    class Meta:
        model = CallRequest
        fields = (
            "id", "vet", "vet_info", "pet", "pet_info", "type", "status",
            "scheduled_at", "address", "lat", "lng", "note",
            "price_agreed", "has_review", "created_at",
        )
        read_only_fields = ("status", "price_agreed", "created_at")

    def get_has_review(self, obj):
        return hasattr(obj, "review")

    def validate_pet(self, pet):
        if pet and pet.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError("Bu hayvon sizga tegishli emas.")
        return pet


# ------------------------- REJIM B: ServiceRequest + Offer -------------------------

class OfferSerializer(serializers.ModelSerializer):
    """Vet taklifi — yaratish (vet) va o'qish (mijoz)."""

    vet_info = VetMiniSerializer(source="vet", read_only=True)

    class Meta:
        model = Offer
        fields = (
            "id", "request", "vet_info", "price", "can_arrive_at",
            "message", "status", "created_at",
        )
        read_only_fields = ("request", "status", "created_at")


class ServiceRequestSerializer(serializers.ModelSerializer):
    """Ochiq so'rov (tender) — yaratish va o'qish."""

    specialization = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all()
    )
    specialization_info = serializers.SerializerMethodField()
    pet = serializers.PrimaryKeyRelatedField(
        queryset=Pet.objects.all(), required=False, allow_null=True
    )
    pet_info = PetMiniSerializer(source="pet", read_only=True)
    offers_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "specialization", "specialization_info", "pet", "pet_info",
            "type", "city", "district", "lat", "lng", "note", "budget_hint",
            "status", "offers_count", "created_at", "expires_at",
        )
        read_only_fields = ("status", "created_at")

    def get_specialization_info(self, obj):
        if obj.specialization:
            return {
                "id": obj.specialization.id,
                "name": obj.specialization.name,
                "icon": obj.specialization.icon,
            }
        return None

    def get_offers_count(self, obj):
        return obj.offers.filter(status=OfferStatus.SENT).count()

    def validate_pet(self, pet):
        if pet and pet.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError("Bu hayvon sizga tegishli emas.")
        return pet
