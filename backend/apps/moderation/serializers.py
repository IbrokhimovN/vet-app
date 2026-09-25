"""Shikoyat serializerlari."""
from rest_framework import serializers

from apps.requests.models import CallRequest, ServiceRequest

from .models import Report


class ReportCreateSerializer(serializers.ModelSerializer):
    call_request = serializers.PrimaryKeyRelatedField(
        queryset=CallRequest.objects.all(), required=False, allow_null=True
    )
    service_request = serializers.PrimaryKeyRelatedField(
        queryset=ServiceRequest.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Report
        fields = ("id", "reported_user", "reason", "comment", "call_request", "service_request")
        read_only_fields = ("id",)

    def validate(self, data):
        user = self.context["request"].user
        if data["reported_user"] == user:
            raise serializers.ValidationError("O'zingizdan shikoyat qila olmaysiz.")
        call = data.get("call_request")
        if call and user.id not in (call.client_id, call.vet.user_id):
            raise serializers.ValidationError("Bu chaqiruv sizga tegishli emas.")
        sr = data.get("service_request")
        if sr:
            is_assigned_vet = sr.assigned_offer and sr.assigned_offer.vet.user_id == user.id
            if user.id != sr.client_id and not is_assigned_vet:
                raise serializers.ValidationError("Bu so'rov sizga tegishli emas.")
        return data
