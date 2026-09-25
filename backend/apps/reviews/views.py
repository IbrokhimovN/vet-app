"""
Izoh view'lari (ARCHITECTURE.md 4.2).

- Mijoz yakunlangan chaqiruvga izoh qoldiradi (bitta marta).
- Vet sahifasida o'sha vetning izohlari ro'yxati ko'rinadi.
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications import services as notify

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer, ReviewUpdateSerializer


class VetReviewListView(generics.ListAPIView):
    """GET /vets/<vet_id>/reviews/ — vetning izohlari (eng yangisi birinchi)."""

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(
            vet_id=self.kwargs["vet_id"]
        ).select_related("client")


class ReviewCreateView(generics.CreateAPIView):
    """POST /reviews/ — mijoz izoh qoldiradi (request, stars, comment)."""

    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        review = serializer.save()
        notify.notify_new_review(review)
        self._review = review

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        # Yaratilgan izohni to'liq (client_name bilan) qaytaramiz.
        return Response(ReviewSerializer(self._review).data, status=201)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    PATCH /reviews/<id>/ — mijoz o'z izohini tahrirlaydi.
    DELETE /reviews/<id>/ — mijoz o'z izohini o'chiradi.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return ReviewSerializer if self.request.method == "GET" else ReviewUpdateSerializer

    def get_queryset(self):
        return Review.objects.filter(client=self.request.user)
