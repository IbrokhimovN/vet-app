"""
So'rov modellari (ARCHITECTURE.md 4.1–4.3).

REJIM A — CallRequest: mijoz vetni to'g'ridan tanlab chaqiradi.
REJIM B — ServiceRequest + Offer: mijoz ochiq so'rov tashlaydi, vetlar taklif beradi (tender).
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class RequestType(models.TextChoices):
    HOME = "home", "Uyga chaqirish"
    ONLINE = "online", "Online konsultatsiya"
    CONTACT = "contact", "Kontakt orqali"


class CallStatus(models.TextChoices):
    PENDING = "pending", "Kutilmoqda"
    ACCEPTED = "accepted", "Qabul qilindi"
    ON_WAY = "on_way", "Yo'lda"
    COMPLETED = "completed", "Yakunlandi"
    REJECTED = "rejected", "Rad etildi"
    CANCELLED = "cancelled", "Bekor qilindi"
    # Vet belgilangan vaqt ichida javob bermadi (tasks.expire_unanswered_calls).
    EXPIRED = "expired", "Muddati tugadi"


class CallRequest(models.Model):
    """REJIM A — to'g'ridan chaqiruv (ARCHITECTURE.md 4.2)."""

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="call_requests"
    )
    vet = models.ForeignKey(
        "vets.VetProfile", on_delete=models.CASCADE, related_name="call_requests"
    )
    pet = models.ForeignKey(
        "pets.Pet", on_delete=models.SET_NULL, null=True, blank=True
    )
    type = models.CharField("Turi", max_length=10, choices=RequestType.choices)
    status = models.CharField(
        "Holat", max_length=10, choices=CallStatus.choices, default=CallStatus.PENDING
    )
    scheduled_at = models.DateTimeField("Belgilangan vaqt", null=True, blank=True)
    address = models.CharField("Manzil", max_length=255, blank=True)
    lat = models.FloatField("Kenglik", null=True, blank=True)
    lng = models.FloatField("Uzunlik", null=True, blank=True)
    note = models.TextField("Izoh", blank=True)
    price_agreed = models.DecimalField(
        "Kelishilgan narx", max_digits=12, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)
    # "Javob tezligi" (pilot KPI) o'lchash uchun: PENDING'dan chiqqan (qabul/rad
    # etilgan) va COMPLETED bo'lgan paytdagi aniq vaqt. `updated_at` bunga yaramaydi —
    # u har status o'zgarishida qayta yoziladi.
    responded_at = models.DateTimeField("Javob berilgan vaqt", null=True, blank=True)
    completed_at = models.DateTimeField("Yakunlangan vaqt", null=True, blank=True)

    class Meta:
        verbose_name = "Chaqiruv (to'g'ridan)"
        verbose_name_plural = "Chaqiruvlar (to'g'ridan)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.get_type_display()} — {self.get_status_display()}"

    # Status o'tishlari (ARCHITECTURE.md 4.2 state machine).
    # EXPIRED faqat tizim tomonidan (tasks.expire_unanswered_calls) qo'yiladi —
    # u shu jadvalni emas, statusni to'g'ridan-to'g'ri tekshiradi.
    TRANSITIONS = {
        CallStatus.PENDING: {CallStatus.ACCEPTED, CallStatus.REJECTED, CallStatus.CANCELLED},
        CallStatus.ACCEPTED: {CallStatus.ON_WAY, CallStatus.COMPLETED, CallStatus.CANCELLED},
        CallStatus.ON_WAY: {CallStatus.COMPLETED, CallStatus.CANCELLED},
    }

    def can_transition(self, new_status) -> bool:
        return new_status in self.TRANSITIONS.get(self.status, set())


class ServiceStatus(models.TextChoices):
    OPEN = "open", "Ochiq"
    ASSIGNED = "assigned", "Vet tayinlandi"
    COMPLETED = "completed", "Yakunlandi"
    CANCELLED = "cancelled", "Bekor qilindi"
    EXPIRED = "expired", "Muddati tugadi"


class ServiceRequest(models.Model):
    """REJIM B — ochiq so'rov / tender (ARCHITECTURE.md 4.3)."""

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests"
    )
    pet = models.ForeignKey(
        "pets.Pet", on_delete=models.SET_NULL, null=True, blank=True
    )
    specialization = models.ForeignKey(
        "vets.Specialization", on_delete=models.SET_NULL, null=True, related_name="requests"
    )
    type = models.CharField("Turi", max_length=10, choices=RequestType.choices)
    city = models.CharField("Shahar", max_length=80, blank=True)
    district = models.CharField("Tuman", max_length=80, blank=True)
    lat = models.FloatField("Kenglik", null=True, blank=True)
    lng = models.FloatField("Uzunlik", null=True, blank=True)
    note = models.TextField("Izoh", blank=True)
    budget_hint = models.DecimalField(
        "Taxminiy byudjet", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    status = models.CharField(
        "Holat", max_length=10, choices=ServiceStatus.choices, default=ServiceStatus.OPEN
    )
    assigned_offer = models.ForeignKey(
        "Offer", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    expires_at = models.DateTimeField("Amal qilish muddati", null=True, blank=True)
    completed_at = models.DateTimeField("Yakunlangan vaqt", null=True, blank=True)

    class Meta:
        verbose_name = "Ochiq so'rov (tender)"
        verbose_name_plural = "Ochiq so'rovlar (tender)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Tender #{self.pk} — {self.get_status_display()}"


class OfferStatus(models.TextChoices):
    SENT = "sent", "Yuborildi"
    ACCEPTED = "accepted", "Qabul qilindi"
    DECLINED = "declined", "Rad etildi"
    WITHDRAWN = "withdrawn", "Qaytarib olindi"


class Offer(models.Model):
    """Vet taklifi — ServiceRequest'ga javob (ARCHITECTURE.md 4.3)."""

    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="offers"
    )
    vet = models.ForeignKey(
        "vets.VetProfile", on_delete=models.CASCADE, related_name="offers"
    )
    price = models.DecimalField("Narx", max_digits=12, decimal_places=2)
    can_arrive_at = models.DateTimeField("Qachon kela oladi", null=True, blank=True)
    message = models.TextField("Xabar", blank=True)
    status = models.CharField(
        "Holat", max_length=10, choices=OfferStatus.choices, default=OfferStatus.SENT
    )
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Taklif"
        verbose_name_plural = "Takliflar"
        ordering = ["price"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "vet"], name="unique_offer_per_vet"
            )
        ]

    def __str__(self):
        return f"Taklif #{self.pk} — {self.price}"
