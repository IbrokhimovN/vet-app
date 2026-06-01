"""pets API marshrutlari (ARCHITECTURE.md 6.2)."""
from django.urls import path

from .views import PetDetailView, PetListCreateView

urlpatterns = [
    path("pets/", PetListCreateView.as_view(), name="pet-list"),
    path("pets/<int:pk>/", PetDetailView.as_view(), name="pet-detail"),
]
