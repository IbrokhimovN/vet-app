"""Hayvon modeli (ARCHITECTURE.md 4-bo'lim)."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

MAX_PHOTO_SIZE_MB = 5
ALLOWED_PHOTO_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]


def validate_photo_size(file):
    """Rasm hajmini cheklaydi (10-bo'lim: xavfsizlik)."""
    limit = MAX_PHOTO_SIZE_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f"Rasm hajmi {MAX_PHOTO_SIZE_MB}MB dan oshmasligi kerak.")


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
    photo = models.ImageField(
        "Rasm", upload_to="pets/", null=True, blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_PHOTO_EXTENSIONS),
            validate_photo_size,
        ],
    )
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Hayvon"
        verbose_name_plural = "Hayvonlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.species})"
