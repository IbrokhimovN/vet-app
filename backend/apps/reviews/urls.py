"""Izoh API marshrutlari (ARCHITECTURE.md 4.2)."""
from django.urls import path

from .views import ReviewCreateView, ReviewDetailView, VetReviewListView

urlpatterns = [
    path("reviews/", ReviewCreateView.as_view(), name="review-create"),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),
    path("vets/<int:vet_id>/reviews/", VetReviewListView.as_view(), name="vet-reviews"),
]
