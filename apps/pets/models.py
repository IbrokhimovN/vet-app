"""Hayvon modeli (ARCHITECTURE.md 4-bo'lim)."""
from django.conf import settings
from django.db import models


class Gender(models.TextChoices):
    MALE = "male", "Erkak"
    FEMALE = "female", "Urg'ochi"
    UNKNOWN = "unknown", "Noma'lum"


class Pet(models.Model):
    """Mijozning uy hayvoni."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pets"
    )
    name = models.CharField("Ism", max_length=80)
    species = models.CharField("Turi", max_length=60, help_text="It, mushuk, qush...")
    breed = models.CharField("Zoti", max_length=80, blank=True)
    age = models.PositiveSmallIntegerField("Yoshi", null=True, blank=True)
    gender = models.CharField(
        "Jinsi", max_length=10, choices=Gender.choices, default=Gender.UNKNOWN
    )
    photo = models.ImageField("Rasm", upload_to="pets/", null=True, blank=True)
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Hayvon"
        verbose_name_plural = "Hayvonlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.species})"
