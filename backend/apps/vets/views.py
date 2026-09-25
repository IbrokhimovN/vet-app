"""
vets view'lari (ARCHITECTURE.md 6.3).

Vet o'z profilini to'ldiradi/tahrirlaydi, xizmatlarini boshqaradi va bo'sh/band
holatini o'zgartiradi. Qidiruv (mijoz tomoni) keyingi bosqichda qo'shiladi.
"""
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Service, Specialization, VetProfile
from .permissions import IsVet
from .serializers import (
    ServiceSerializer,
    SpecializationSerializer,
    VetDetailSerializer,
    VetListSerializer,
    VetProfileSerializer,
)
from .utils import haversine_km, region_q


def _parse_coord(value):
    """Query'dan kelgan lat/lng ni float'ga aylantiradi (xato bo'lsa None)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class SpecializationListView(generics.ListAPIView):
    """Barcha mutaxassisliklar ro'yxati (ikkala Mini App uchun)."""

    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class VetSearchView(generics.ListAPIView):
    """
    Mijoz vetlarni qidiradi (ARCHITECTURE.md 6.2).

    Query parametrlar:
      spec=<slug>        — mutaxassislik bo'yicha
      type=home|online   — chaqiruv turi bo'yicha
      city=<matn>        — shahar bo'yicha
      q=<matn>           — ism / klinika bo'yicha qidiruv
      lat=&lng=          — masofa hisoblash uchun mijoz joylashuvi
      sort=distance|rating (default: rating)
    TOP vetlar har doim oldinda chiqadi.
    """

    serializer_class = VetListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            VetProfile.objects.select_related("user")
            .prefetch_related("specializations", "services")
        )
        p = self.request.query_params

        if p.get("spec"):
            qs = qs.filter(specializations__slug=p["spec"])
        if p.get("type") == "home":
            qs = qs.filter(accepts_home_visit=True)
        elif p.get("type") == "online":
            qs = qs.filter(accepts_online=True)
        if p.get("city"):
            qs = qs.filter(region_q("city", p["city"]))
        if p.get("q"):
            term = p["q"]
            qs = qs.filter(
                Q(user__first_name__icontains=term)
                | Q(user__last_name__icontains=term)
                | Q(clinic_name__icontains=term)
            )
        return qs.distinct()

    def list(self, request, *args, **kwargs):
        queryset = list(self.get_queryset())
        p = request.query_params
        lat, lng = _parse_coord(p.get("lat")), _parse_coord(p.get("lng"))

        # Har bir vetga masofani biriktiramiz (Haversine).
        for vet in queryset:
            vet.distance_km = haversine_km(lat, lng, vet.lat, vet.lng)

        # Saralash: TOP doim oldinda, keyin tanlangan mezon bo'yicha.
        sort = p.get("sort", "rating")
        if sort == "distance" and lat is not None and lng is not None:
            queryset.sort(
                key=lambda v: (
                    not v.is_top,
                    v.distance_km if v.distance_km is not None else float("inf"),
                )
            )
        else:
            queryset.sort(key=lambda v: (not v.is_top, -float(v.rating_avg)))

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class VetDetailView(generics.RetrieveAPIView):
    """Vet sahifasi (mijoz tomoni) — to'liq ma'lumot + xizmatlar."""

    serializer_class = VetDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = VetProfile.objects.select_related("user").prefetch_related(
        "specializations", "services"
    )


class VetMeView(generics.RetrieveUpdateAPIView):
    """
    Vetning o'z profili: GET / PUT / PATCH.
    Profil hali bo'lmasa — birinchi murojaatda avtomatik yaratiladi.
    """

    serializer_class = VetProfileSerializer
    permission_classes = [IsVet]

    def get_object(self):
        profile, _ = VetProfile.objects.get_or_create(user=self.request.user)
        return profile


class VetAvailabilityView(APIView):
    """Vetning bo'sh/band holatini o'zgartiradi."""

    permission_classes = [IsVet]

    def put(self, request):
        profile, _ = VetProfile.objects.get_or_create(user=request.user)
        is_available = request.data.get("is_available")
        if not isinstance(is_available, bool):
            return Response(
                {"detail": "is_available (true/false) talab qilinadi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile.is_available = is_available
        profile.save(update_fields=["is_available"])
        return Response({"is_available": profile.is_available})


class ServiceListCreateView(generics.ListCreateAPIView):
    """Vetning xizmatlari: ro'yxat va qo'shish."""

    serializer_class = ServiceSerializer
    permission_classes = [IsVet]
    pagination_class = None

    def _profile(self):
        profile, _ = VetProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_queryset(self):
        return Service.objects.filter(vet=self._profile())

    def perform_create(self, serializer):
        serializer.save(vet=self._profile())


class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Bitta xizmatni tahrirlash / o'chirish (faqat egasi)."""

    serializer_class = ServiceSerializer
    permission_classes = [IsVet]

    def get_queryset(self):
        return Service.objects.filter(vet__user=self.request.user)
