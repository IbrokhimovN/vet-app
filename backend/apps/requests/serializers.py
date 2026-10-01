"""requests serializerlari (ARCHITECTURE.md 6.2, 6.3)."""
from rest_framework import serializers

from apps.pets.models import Pet
from apps.vets.models import Specialization, VetProfile
from apps.vets.utils import haversine_km

from .models import CallRequest, Offer, OfferStatus, ServiceRequest, ServiceStatus


class VetMiniSerializer(serializers.ModelSerializer):
    """Javoblarda vet haqida qisqa ma'lumot."""

    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = VetProfile
        fields = ("id", "user_id", "full_name", "clinic_name", "rating_avg", "city")


class PetMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ("id", "name", "species")


class ClientMiniSerializer(serializers.Serializer):
    """Javoblarda mijoz haqida qisqa ma'lumot (vet tomoniga)."""

    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.first_name or obj.username


# Chaqiruv/tender endi rasman bog'langan (qabul qilingan/tayinlangan) bo'lsagina
# telefon raqami ko'rsatiladi — undan oldin (ochiq lenta, hali javob berilmagan
# chaqiruv) ikkala tomon ham bir-birining raqamini ko'rmaydi (10-bo'lim: pilotda
# aniqlangan kamchilik — avval hech qanday holatda ko'rinmas edi).
CONNECTED_CALL_STATUSES = ("accepted", "on_way", "completed")


def _hide_exact_location(data, fields):
    """Mijozning aniq joyi (amalda uy manzili) telefon kabi bog'lanishgacha
    yashiriladi — vetga faqat masofa ko'rsatiladi."""
    data["location_hidden"] = any(data.get(f) not in (None, "") for f in fields)
    for f in fields:
        data[f] = "" if f == "address" else None
    return data


# ------------------------- REJIM A: CallRequest -------------------------

class CallRequestSerializer(serializers.ModelSerializer):
    """To'g'ridan chaqiruv — yaratish va o'qish."""

    vet = serializers.PrimaryKeyRelatedField(queryset=VetProfile.objects.all())
    vet_info = serializers.SerializerMethodField()
    client_info = serializers.SerializerMethodField()
    pet = serializers.PrimaryKeyRelatedField(
        queryset=Pet.objects.all(), required=False, allow_null=True
    )
    pet_info = PetMiniSerializer(source="pet", read_only=True)
    has_review = serializers.SerializerMethodField()
    my_review = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = CallRequest
        fields = (
            "id", "vet", "vet_info", "client_info", "pet", "pet_info", "type", "status",
            "scheduled_at", "address", "lat", "lng", "distance_km", "note",
            "price_agreed", "has_review", "my_review", "created_at",
            "responded_at", "completed_at",
        )
        read_only_fields = ("status", "price_agreed", "created_at", "responded_at", "completed_at")

    def get_has_review(self, obj):
        return hasattr(obj, "review")

    def get_my_review(self, obj):
        review = getattr(obj, "review", None)
        if not review:
            return None
        return {"id": review.id, "stars": review.stars, "comment": review.comment}

    def get_distance_km(self, obj):
        return haversine_km(obj.vet.lat, obj.vet.lng, obj.lat, obj.lng)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        request = self.context.get("request")
        viewer_is_client = request is not None and request.user.id == obj.client_id
        if not viewer_is_client and obj.status not in CONNECTED_CALL_STATUSES:
            _hide_exact_location(data, ("address", "lat", "lng"))
        else:
            data["location_hidden"] = False
        return data

    def get_vet_info(self, obj):
        data = VetMiniSerializer(obj.vet).data
        if obj.status in CONNECTED_CALL_STATUSES:
            data["phone"] = obj.vet.user.phone
        return data

    def get_client_info(self, obj):
        data = ClientMiniSerializer(obj.client).data
        if obj.status in CONNECTED_CALL_STATUSES:
            data["phone"] = obj.client.phone
        return data

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
    assigned_offer_info = serializers.SerializerMethodField()
    has_review = serializers.SerializerMethodField()
    my_review = serializers.SerializerMethodField()
    my_offer = serializers.SerializerMethodField()
    client_info = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "specialization", "specialization_info", "pet", "pet_info",
            "type", "city", "district", "lat", "lng", "distance_km", "note", "budget_hint",
            "status", "offers_count", "assigned_offer_info", "has_review", "my_review", "my_offer",
            "client_info", "created_at", "expires_at", "completed_at",
        )
        read_only_fields = ("status", "created_at", "completed_at")

    def get_specialization_info(self, obj):
        if obj.specialization:
            return {
                "id": obj.specialization.id,
                "name": obj.specialization.name,
                "icon": obj.specialization.icon,
            }
        return None

    def get_distance_km(self, obj):
        request = self.context.get("request")
        profile = getattr(request.user, "vet_profile", None) if request else None
        if not profile:
            return None
        return haversine_km(profile.lat, profile.lng, obj.lat, obj.lng)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        request = self.context.get("request")
        user_id = request.user.id if request else None
        offer = obj.assigned_offer
        is_winner = (
            obj.status in (ServiceStatus.ASSIGNED, ServiceStatus.COMPLETED)
            and offer is not None and offer.vet.user_id == user_id
        )
        if user_id != obj.client_id and not is_winner:
            _hide_exact_location(data, ("lat", "lng"))
        else:
            data["location_hidden"] = False
        return data

    def get_offers_count(self, obj):
        return obj.offers.filter(status=OfferStatus.SENT).count()

    def get_assigned_offer_info(self, obj):
        offer = obj.assigned_offer
        if not offer:
            return None
        # Tayinlangandan keyin ikkala tomon ham bir-biriga qo'ng'iroq qila olishi
        # kerak, shuning uchun bu yerda (faqat "assigned_offer" borligining o'zi
        # allaqachon tayinlanganini bildiradi) vet telefoni ham qo'shiladi.
        vet_info = VetMiniSerializer(offer.vet).data
        vet_info["phone"] = offer.vet.user.phone
        return {
            "id": offer.id,
            "price": offer.price,
            "vet_info": vet_info,
        }

    def get_has_review(self, obj):
        return hasattr(obj, "review")

    def get_my_review(self, obj):
        review = getattr(obj, "review", None)
        if not review:
            return None
        return {"id": review.id, "stars": review.stars, "comment": review.comment}

    def get_my_offer(self, obj):
        """Vet o'zi shu so'rovga taklif yuborgan bo'lsa — uni qaytaradi (feed uchun)."""
        user = self.context["request"].user
        if not user.is_vet:
            return None
        offer = next(
            (o for o in obj.offers.all() if o.vet.user_id == user.id and o.status != OfferStatus.WITHDRAWN),
            None,
        )
        if not offer:
            return None
        return {"id": offer.id, "price": offer.price, "status": offer.status}

    def get_client_info(self, obj):
        """
        Mijoz ma'lumoti faqat g'olib vetga, va faqat tayinlangach ko'rinadi —
        ochiq tender lentasida hamma vetga mijoz shaxsi oshkor qilinmaydi.
        Shu maydon bo'lmagani uchun oldin g'olib vet mijozdan shikoyat qila
        olmas edi (10-bo'lim: pilotda aniqlangan kamchilik).
        """
        request = self.context.get("request")
        if not request or obj.status not in (ServiceStatus.ASSIGNED, ServiceStatus.COMPLETED):
            return None
        offer = obj.assigned_offer
        if not offer or offer.vet.user_id != request.user.id:
            return None
        return {
            "id": obj.client.id,
            "full_name": obj.client.get_full_name() or obj.client.username,
            "phone": obj.client.phone,
        }

    def validate_pet(self, pet):
        if pet and pet.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError("Bu hayvon sizga tegishli emas.")
        return pet
