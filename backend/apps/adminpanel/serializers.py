"""Admin panel uchun serializerlar — har biri jadvalda ko'rsatish uchun yetarli
ma'lumot beradi, ortiqcha nested qatlamlarsiz."""
from rest_framework import serializers

from apps.accounts.models import User
from apps.moderation.models import Report
from apps.notifications.models import Notification
from apps.pets.models import Pet
from apps.requests.models import CallRequest, ServiceRequest
from apps.reviews.models import Review
from apps.vets.models import VetProfile


def display_name(user):
    return user.get_full_name() or user.username


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "full_name", "username", "role", "phone", "telegram_id",
            "language", "photo", "is_active", "date_joined",
        )

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.first_name or obj.username


class AdminVetSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    photo = serializers.ImageField(source="user.photo", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    specializations = serializers.StringRelatedField(many=True, read_only=True)
    license_document = serializers.FileField(read_only=True)

    class Meta:
        model = VetProfile
        fields = (
            "id", "full_name", "username", "phone", "photo", "is_active",
            "city", "clinic_name", "experience_years", "specializations",
            "is_verified", "is_available", "license_document",
            "is_top", "top_until", "wallet_balance",
            "rating_avg", "rating_count", "created_at",
        )

    def get_full_name(self, obj):
        return display_name(obj.user)


class AdminPetMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ("id", "name", "species")


class AdminCallSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    vet_name = serializers.SerializerMethodField()
    pet_info = AdminPetMiniSerializer(source="pet", read_only=True)

    class Meta:
        model = CallRequest
        fields = (
            "id", "client_name", "vet_name", "pet_info", "type", "status",
            "address", "note", "price_agreed", "scheduled_at", "created_at",
        )

    def get_client_name(self, obj):
        return display_name(obj.client)

    def get_vet_name(self, obj):
        return display_name(obj.vet.user)


class AdminServiceRequestSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    specialization_name = serializers.CharField(source="specialization.name", read_only=True)
    offers_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "client_name", "specialization_name", "type", "city",
            "status", "budget_hint", "offers_count", "created_at",
        )

    def get_client_name(self, obj):
        return display_name(obj.client)

    def get_offers_count(self, obj):
        return obj.offers.count()


class AdminReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    vet_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "client_name", "vet_name", "stars", "comment", "created_at")

    def get_client_name(self, obj):
        return display_name(obj.client)

    def get_vet_name(self, obj):
        return display_name(obj.vet.user)


class AdminReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.SerializerMethodField()
    reported_name = serializers.SerializerMethodField()
    reported_user_id = serializers.IntegerField(source="reported_user.id", read_only=True)

    class Meta:
        model = Report
        fields = (
            "id", "reporter_name", "reported_name", "reported_user_id",
            "reason", "comment", "is_resolved", "created_at",
        )

    def get_reporter_name(self, obj):
        return obj.reporter.get_full_name() or obj.reporter.username

    def get_reported_name(self, obj):
        return obj.reported_user.get_full_name() or obj.reported_user.username


class AdminNotificationSerializer(serializers.ModelSerializer):
    """Yetkazish holatini kuzatish uchun (10-bo'lim: pilot kamchiligi)."""

    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id", "recipient_name", "kind", "bot", "title", "body",
            "is_sent", "error", "created_at", "sent_at",
        )

    def get_recipient_name(self, obj):
        return display_name(obj.recipient)
