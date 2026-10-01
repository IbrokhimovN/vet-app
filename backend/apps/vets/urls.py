"""vets API marshrutlari (ARCHITECTURE.md 6.3)."""
from django.urls import path

from .views import (
    ClinicDetailView,
    ClinicListView,
    ServiceDetailView,
    ServiceListCreateView,
    SpecializationListView,
    VetAvailabilityView,
    VetDetailView,
    VetMeView,
    VetSearchView,
)

urlpatterns = [
    path("specializations/", SpecializationListView.as_view(), name="specialization-list"),
    # Vet o'z profili (me/ — int converter bilan to'qnashmaydi)
    path("vets/me/", VetMeView.as_view(), name="vet-me"),
    path("vets/me/availability/", VetAvailabilityView.as_view(), name="vet-availability"),
    path("vets/me/services/", ServiceListCreateView.as_view(), name="vet-services"),
    path("vets/me/services/<int:pk>/", ServiceDetailView.as_view(), name="vet-service-detail"),
    # Mijoz tomoni: qidiruv va sahifa
    path("vets/", VetSearchView.as_view(), name="vet-search"),
    path("vets/<int:pk>/", VetDetailView.as_view(), name="vet-detail"),
    path("clinics/", ClinicListView.as_view(), name="clinic-list"),
    path("clinics/<int:pk>/", ClinicDetailView.as_view(), name="clinic-detail"),
]
