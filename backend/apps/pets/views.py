"""pets view'lari (ARCHITECTURE.md 6.2) — mijoz o'z hayvonlarini boshqaradi."""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Pet
from .serializers import PetSerializer


class PetListCreateView(generics.ListCreateAPIView):
    serializer_class = PetSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)
