"""
Izoh / reyting modeli (ARCHITECTURE.md 3, 4.2).

Mijoz YAKUNLANGAN chaqiruvga (REJIM A) YOKI yakunlangan ochiq so'rovga
(REJIM B — tender) bitta izoh qoldiradi. Aynan bittasi to'ldirilishi shart.
Har izoh saqlanganda/o'chirilganda vetning `rating_avg`/`rating_count`
qayta hisoblanadi.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    vet = models.ForeignKey(
        "vets.VetProfile", on_delete=models.CASCADE, related_name="reviews"
    )
    request = models.OneToOneField(
        "requests.CallRequest", on_delete=models.CASCADE, related_name="review",
        null=True, blank=True,
    )
    service_request = models.OneToOneField(
        "requests.ServiceRequest", on_delete=models.CASCADE, related_name="review",
        null=True, blank=True,
    )
    stars = models.PositiveSmallIntegerField(
        "Baho", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Izoh"
        verbose_name_plural = "Izohlar"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(request__isnull=False, service_request__isnull=True)
                    | models.Q(request__isnull=True, service_request__isnull=False)
                ),
                name="review_exactly_one_source",
            )
        ]

    def __str__(self):
        return f"{self.stars}★ -> vet#{self.vet_id}"
