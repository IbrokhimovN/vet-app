"""
requests view'lari (ARCHITECTURE.md 4.2–4.3, 6.2–6.3).

REJIM A — CallRequest: to'g'ridan chaqiruv + status oqimi.
REJIM B — ServiceRequest/Offer: tender (ochiq so'rov -> takliflar -> tanlash).
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications import services as notify
from apps.vets.models import VetProfile
from apps.vets.utils import region_q

from .models import (
    CallRequest,
    CallStatus,
    Offer,
    OfferStatus,
    ServiceRequest,
    ServiceStatus,
)
from .permissions import IsClient, IsVet
from .serializers import (
    CallRequestSerializer,
    OfferSerializer,
    ServiceRequestSerializer,
)
from .throttles import CreateOnlyRateThrottle


def _vet_profile(user):
    profile, _ = VetProfile.objects.get_or_create(user=user)
    return profile


# ============================ REJIM A: CallRequest ============================

class CallRequestListCreateView(generics.ListCreateAPIView):
    """
    POST — mijoz to'g'ridan chaqiruv yaratadi.
    GET ?role=client — mening chaqiruvlarim; ?role=vet — menga kelganlar.
    """

    serializer_class = CallRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [CreateOnlyRateThrottle]
    throttle_scope = "call-create"

    def get_queryset(self):
        user = self.request.user
        role = self.request.query_params.get("role")
        base = CallRequest.objects.select_related("vet__user", "pet", "client")
        if role == "vet" or (role is None and user.is_vet):
            return base.filter(vet__user=user)
        return base.filter(client=user)

    def perform_create(self, serializer):
        if not self.request.user.is_client:
            raise PermissionDenied("Chaqiruvni faqat mijoz yaratadi.")
        call = serializer.save(client=self.request.user)
        notify.notify_new_call(call)


class CallRequestActionView(APIView):
    """
    Chaqiruv holatini o'zgartiradi (ARCHITECTURE.md 4.2):
      vet:    accept | reject | on_way | complete
      mijoz:  cancel
    """

    permission_classes = [IsAuthenticated]

    ACTION_STATUS = {
        "accept": CallStatus.ACCEPTED,
        "reject": CallStatus.REJECTED,
        "on_way": CallStatus.ON_WAY,
        "complete": CallStatus.COMPLETED,
        "cancel": CallStatus.CANCELLED,
    }

    def post(self, request, pk, action):
        if action not in self.ACTION_STATUS:
            return Response({"detail": "Noma'lum amal."}, status=400)
        call = generics.get_object_or_404(CallRequest, pk=pk)
        user = request.user

        if action == "cancel":
            if call.client_id != user.id:
                raise PermissionDenied("Faqat mijoz bekor qila oladi.")
        else:  # vet amallari
            if call.vet.user_id != user.id:
                raise PermissionDenied("Bu chaqiruv sizga tegishli emas.")

        new_status = self.ACTION_STATUS[action]
        if not call.can_transition(new_status):
            raise ValidationError(
                f"'{call.get_status_display()}' holatidan bu amal mumkin emas."
            )
        call.status = new_status
        update_fields = ["status", "updated_at"]
        now = timezone.now()
        # "Javob tezligi" — PENDING'dan birinchi marta chiqqan payt (qabul yoki rad).
        if call.status in (CallStatus.ACCEPTED, CallStatus.REJECTED) and not call.responded_at:
            call.responded_at = now
            update_fields.append("responded_at")
        if call.status == CallStatus.COMPLETED and not call.completed_at:
            call.completed_at = now
            update_fields.append("completed_at")
        call.save(update_fields=update_fields)
        notify.notify_call_status(call, actor=user)
        return Response(CallRequestSerializer(call, context={"request": request}).data)


class CallRequestSetPriceView(APIView):
    """
    POST /requests/<pk>/price/ — vet kelishilgan narxni yozadi.
    To'g'ridan chaqiruvda narx odatda telefon/joyida kelishiladi (ilova ichida
    to'lov yo'q — 12-bo'lim), lekin bu maydon avval hech qayerda to'ldirilmasdi:
    admin panelda "o'rtacha ish narxi" statistikasi hech qachon hisoblanmasdi
    (10-bo'lim: pilotda aniqlangan kamchilik). Vet ishni qabul qilgandan keyin,
    kelishilgan narxni shu orqali kiritadi.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        call = generics.get_object_or_404(CallRequest, pk=pk)
        if call.vet.user_id != request.user.id:
            raise PermissionDenied("Bu chaqiruv sizga tegishli emas.")
        if call.status not in (CallStatus.ACCEPTED, CallStatus.ON_WAY, CallStatus.COMPLETED):
            raise ValidationError("Narxni faqat qabul qilingan chaqiruvda kiritish mumkin.")
        price = request.data.get("price_agreed")
        if price in (None, ""):
            raise ValidationError({"price_agreed": "Narx kiritilishi shart."})
        try:
            price = Decimal(str(price))
        except InvalidOperation:
            raise ValidationError({"price_agreed": "Narx noto'g'ri formatda."})
        if price < 0:
            raise ValidationError({"price_agreed": "Narx manfiy bo'lishi mumkin emas."})
        call.price_agreed = price
        call.save(update_fields=["price_agreed", "updated_at"])
        return Response(CallRequestSerializer(call, context={"request": request}).data)


# ====================== REJIM B: ServiceRequest + Offer ======================

class ServiceRequestListCreateView(generics.ListCreateAPIView):
    """POST — mijoz ochiq so'rov (tender) yaratadi. GET — mening so'rovlarim."""

    serializer_class = ServiceRequestSerializer
    permission_classes = [IsClient]
    throttle_classes = [CreateOnlyRateThrottle]
    throttle_scope = "tender-create"

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            client=self.request.user
        ).select_related("specialization", "pet", "assigned_offer__vet__user", "review")

    def perform_create(self, serializer):
        sr = serializer.save(client=self.request.user)
        notify.notify_new_tender(sr)


class ServiceRequestCancelView(APIView):
    """Mijoz tenderni bekor qiladi."""

    permission_classes = [IsClient]

    def post(self, request, pk):
        sr = generics.get_object_or_404(ServiceRequest, pk=pk, client=request.user)
        if sr.status not in (ServiceStatus.OPEN, ServiceStatus.ASSIGNED):
            raise ValidationError("Bu so'rovni bekor qilib bo'lmaydi.")
        sr.status = ServiceStatus.CANCELLED
        sr.save(update_fields=["status"])
        return Response({"status": sr.status})


class ServiceRequestOffersView(generics.ListAPIView):
    """Mijoz o'z so'roviga kelgan takliflarni ko'radi."""

    serializer_class = OfferSerializer
    permission_classes = [IsClient]
    pagination_class = None

    def get_queryset(self):
        sr = generics.get_object_or_404(
            ServiceRequest, pk=self.kwargs["pk"], client=self.request.user
        )
        # Eng arzonidan qimmatiga — mijoz taklflarni osongina solishtira olsin.
        return sr.offers.select_related("vet__user").exclude(
            status=OfferStatus.WITHDRAWN
        ).order_by("price")


class OfferAcceptView(APIView):
    """Mijoz taklifni qabul qiladi -> vet tayinlanadi, qolgan takliflar rad etiladi."""

    permission_classes = [IsClient]

    @transaction.atomic
    def post(self, request, pk):
        offer = generics.get_object_or_404(
            Offer.objects.select_related("request"), pk=pk
        )
        sr = offer.request
        if sr.client_id != request.user.id:
            raise PermissionDenied("Bu so'rov sizga tegishli emas.")
        if sr.status != ServiceStatus.OPEN:
            raise ValidationError("So'rov ochiq emas.")

        offer.status = OfferStatus.ACCEPTED
        offer.save(update_fields=["status"])
        # Rad etiladigan takliflarni (xabar uchun) avval to'plab olamiz.
        declined = list(
            sr.offers.exclude(pk=offer.pk)
            .filter(status=OfferStatus.SENT)
            .select_related("vet__user")
        )
        sr.offers.exclude(pk=offer.pk).update(status=OfferStatus.DECLINED)
        sr.status = ServiceStatus.ASSIGNED
        sr.assigned_offer = offer
        sr.save(update_fields=["status", "assigned_offer"])

        transaction.on_commit(lambda: notify.notify_offer_accepted(offer))
        for d in declined:
            transaction.on_commit(lambda d=d: notify.notify_offer_declined(d))
        return Response(OfferSerializer(offer).data)


class ServiceRequestFeedView(generics.ListAPIView):
    """Vetga mos ochiq so'rovlar lentasi (mutaxassislik bo'yicha)."""

    serializer_class = ServiceRequestSerializer
    permission_classes = [IsVet]

    def get_queryset(self):
        profile = _vet_profile(self.request.user)
        spec_ids = profile.specializations.values_list("id", flat=True)
        qs = ServiceRequest.objects.filter(status=ServiceStatus.OPEN).select_related(
            "specialization", "pet"
        ).prefetch_related("offers__vet__user")
        if spec_ids:
            qs = qs.filter(specialization_id__in=spec_ids)
        # Faqat vetning o'z viloyatidagi (yoki viloyati ko'rsatilmagan) so'rovlar
        if profile.city:
            qs = qs.filter(region_q("city", profile.city) | Q(city=""))
        # Muddati o'tmaganlar
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        return qs


class ServiceRequestWonView(generics.ListAPIView):
    """Vet g'olib bo'lgan (o'ziga tayinlangan) ochiq so'rovlar ro'yxati."""

    serializer_class = ServiceRequestSerializer
    permission_classes = [IsVet]
    pagination_class = None

    def get_queryset(self):
        profile = _vet_profile(self.request.user)
        return (
            ServiceRequest.objects.filter(
                assigned_offer__vet=profile,
                status__in=[ServiceStatus.ASSIGNED, ServiceStatus.COMPLETED],
            )
            .select_related("specialization", "pet", "assigned_offer__vet__user", "review")
            .order_by("-created_at")
        )


class ServiceRequestCompleteView(APIView):
    """Tayinlangan vet ochiq so'rovni yakunlaydi (mijoz keyin baholashi mumkin)."""

    permission_classes = [IsVet]

    def post(self, request, pk):
        sr = generics.get_object_or_404(ServiceRequest, pk=pk)
        profile = _vet_profile(request.user)
        if sr.status != ServiceStatus.ASSIGNED or not sr.assigned_offer or sr.assigned_offer.vet_id != profile.id:
            raise PermissionDenied("Bu so'rovni yakunlash huquqingiz yo'q.")
        sr.status = ServiceStatus.COMPLETED
        sr.completed_at = timezone.now()
        sr.save(update_fields=["status", "completed_at"])
        notify.notify_service_completed(sr)
        return Response(ServiceRequestSerializer(sr, context={"request": request}).data)


class OfferCreateView(APIView):
    """Vet ochiq so'rovga taklif yuboradi."""

    permission_classes = [IsVet]

    def post(self, request, pk):
        sr = generics.get_object_or_404(ServiceRequest, pk=pk)
        if sr.status != ServiceStatus.OPEN:
            raise ValidationError("So'rov endi ochiq emas.")
        profile = _vet_profile(request.user)
        if sr.offers.filter(vet=profile).exists():
            raise ValidationError("Siz bu so'rovga allaqachon taklif yuborgansiz.")

        serializer = OfferSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        offer = serializer.save(request=sr, vet=profile)
        notify.notify_new_offer(offer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OfferWithdrawView(APIView):
    """Vet o'z taklifini qaytarib oladi."""

    permission_classes = [IsVet]

    def post(self, request, pk):
        offer = generics.get_object_or_404(Offer, pk=pk, vet__user=request.user)
        if offer.status != OfferStatus.SENT:
            raise ValidationError("Bu taklifni qaytarib bo'lmaydi.")
        offer.status = OfferStatus.WITHDRAWN
        offer.save(update_fields=["status"])
        return Response({"status": offer.status})
