"""
Ilova ichidagi bildirishnoma lentasi (ARCHITECTURE.md 14 — headless API).

Telegram push'dan tashqari, har bir klient (Mini App / mobil / web) shu API orqali
o'z bildirishnomalarini ko'radi va o'qilgan deb belgilaydi.
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """GET — mening bildirishnomalarim (?unread=1 — faqat o'qilmaganlar)."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("unread") in ("1", "true"):
            qs = qs.filter(is_read=False)
        return qs


class NotificationUnreadCountView(APIView):
    """GET — o'qilmagan bildirishnomalar soni (badge uchun)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({"unread": count})


class NotificationReadView(APIView):
    """POST — bittasini yoki barchasini o'qilgan deb belgilaydi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        qs = Notification.objects.filter(recipient=request.user, is_read=False)
        if pk is not None:
            qs = qs.filter(pk=pk)
        updated = qs.update(is_read=True)
        return Response({"updated": updated})
