"""
Shikoyat modeli — mijoz yomon vetdan, yoki vet yomon mijozdan shikoyat qiladi.

MVP: faqat qayd qilib boradi (admin ko'rib chiqadi). Avtomatik bloklash yo'q —
takroriy shikoyatlar to'plansa, admin qo'lda `User.is_active`ni o'chirishi mumkin.
"""
from django.conf import settings
from django.db import models


class ReportReason(models.TextChoices):
    NO_SHOW = "no_show", "Kelmadi / javob bermadi"
    RUDE = "rude", "Muomalasi yomon"
    FRAUD = "fraud", "Firibgarlik / pul talab qildi"
    QUALITY = "quality", "Xizmat sifati past"
    OTHER = "other", "Boshqa"


class Report(models.Model):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made"
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_received"
    )
    reason = models.CharField("Sabab", max_length=20, choices=ReportReason.choices)
    comment = models.TextField("Izoh", blank=True)

    # Ixtiyoriy bog'lanish — qaysi chaqiruv/so'rov bo'yicha shikoyat qilingani.
    call_request = models.ForeignKey(
        "requests.CallRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    service_request = models.ForeignKey(
        "requests.ServiceRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    is_resolved = models.BooleanField("Ko'rib chiqilgan", default=False)

    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Shikoyat"
        verbose_name_plural = "Shikoyatlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reporter_id} -> {self.reported_user_id}: {self.get_reason_display()}"
