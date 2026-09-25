"""
Bildirishnoma modeli (ARCHITECTURE.md 7-bo'lim).

Har bir bildirishnoma DB'da saqlanadi (audit + ilova ichidagi lenta uchun) va
Celery orqali Telegram'ga yetkaziladi. `bot` qabul qiluvchi rolidan kelib chiqadi.
"""
from django.conf import settings
from django.db import models


class NotificationKind(models.TextChoices):
    CALL_NEW = "call_new", "Yangi chaqiruv"
    CALL_STATUS = "call_status", "Chaqiruv holati o'zgardi"
    TENDER_NEW = "tender_new", "Yangi tender"
    OFFER_NEW = "offer_new", "Yangi taklif"
    OFFER_ACCEPTED = "offer_accepted", "Taklif qabul qilindi"
    OFFER_DECLINED = "offer_declined", "Taklif rad etildi"
    SERVICE_COMPLETED = "service_completed", "Ochiq so'rov yakunlandi"
    REVIEW_NEW = "review_new", "Yangi izoh"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField("Turi", max_length=20, choices=NotificationKind.choices)
    title = models.CharField("Sarlavha", max_length=120, blank=True)
    body = models.TextField("Matn", blank=True)
    bot = models.CharField("Bot", max_length=10, default="client")  # client | vet

    is_read = models.BooleanField("O'qilgan", default=False)
    is_sent = models.BooleanField("Yuborilgan", default=False)
    sent_at = models.DateTimeField("Yuborilgan vaqt", null=True, blank=True)
    error = models.TextField("Xatolik", blank=True)

    # Tegishli obyektlar (ixtiyoriy bog'lanish).
    call_request = models.ForeignKey(
        "requests.CallRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    service_request = models.ForeignKey(
        "requests.ServiceRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    offer = models.ForeignKey(
        "requests.Offer", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} -> {self.recipient_id}"
