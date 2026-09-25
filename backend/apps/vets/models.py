"""
Veterinar modellari (ARCHITECTURE.md 4-bo'lim).

Specialization — mutaxassislik / hayvon turi (it, mushuk, qoramol...).
VetProfile     — veterinarning to'liq profili (User bilan 1:1).
Service        — vet ko'rsatadigan xizmat va narxi.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

MAX_DOCUMENT_SIZE_MB = 10
ALLOWED_DOCUMENT_EXTENSIONS = ["jpg", "jpeg", "png", "pdf"]


def validate_document_size(file):
    """Hujjat hajmini cheklaydi (10-bo'lim: xavfsizlik)."""
    limit = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f"Fayl hajmi {MAX_DOCUMENT_SIZE_MB}MB dan oshmasligi kerak.")


class Specialization(models.Model):
    """Mutaxassislik yoki hayvon turi (ustabor'dagi kategoriya ekvivalenti)."""

    name = models.CharField("Nomi", max_length=80, unique=True)
    slug = models.SlugField("Slug", max_length=90, unique=True)
    icon = models.CharField("Ikon (emoji yoki nom)", max_length=40, blank=True)

    class Meta:
        verbose_name = "Mutaxassislik"
        verbose_name_plural = "Mutaxassisliklar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class VetProfile(models.Model):
    """Veterinarning profili. Vet Mini App orqali to'ldiriladi."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vet_profile",
    )
    bio = models.TextField("Bio", blank=True)
    experience_years = models.PositiveSmallIntegerField("Tajriba (yil)", default=0)
    clinic_name = models.CharField("Klinika nomi", max_length=150, blank=True)

    # Joylashuv (oddiy geo — Haversine, ARCHITECTURE.md 8-bo'lim)
    lat = models.FloatField("Kenglik", null=True, blank=True)
    lng = models.FloatField("Uzunlik", null=True, blank=True)
    address = models.CharField("Manzil", max_length=255, blank=True)
    city = models.CharField("Shahar", max_length=80, blank=True)
    district = models.CharField("Tuman", max_length=80, blank=True)

    # Holat
    is_verified = models.BooleanField("Tasdiqlangan", default=False)
    is_available = models.BooleanField("Bo'sh (ish qabul qiladi)", default=True)
    # Diplom/litsenziya skani — admin "Tasdiqlash"dan oldin shuni ko'rib chiqishi
    # kerak (10-bo'lim: avval tasdiqlash faqat matnga ishonib qilinardi).
    license_document = models.FileField(
        "Diplom / litsenziya", upload_to="vet_licenses/", null=True, blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS),
            validate_document_size,
        ],
    )

    # Reyting (reviews app yangilab turadi)
    rating_avg = models.DecimalField(
        "O'rtacha reyting", max_digits=3, decimal_places=2, default=Decimal("0")
    )
    rating_count = models.PositiveIntegerField("Izohlar soni", default=0)

    specializations = models.ManyToManyField(
        Specialization, related_name="vets", blank=True
    )

    # Chaqiruv turlari (ARCHITECTURE.md: home / online / contact)
    accepts_home_visit = models.BooleanField("Uyga boradi", default=True)
    accepts_online = models.BooleanField("Online konsultatsiya", default=True)

    # --- Monetizatsiya (12-bo'lim) — MVP'da ishlatilmaydi, zaxira ---
    is_top = models.BooleanField("TOP joylashuv", default=False)
    top_until = models.DateTimeField("TOP muddati", null=True, blank=True)
    wallet_balance = models.DecimalField(
        "Hamyon balansi", max_digits=12, decimal_places=2, default=Decimal("0")
    )

    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    class Meta:
        verbose_name = "Veterinar profili"
        verbose_name_plural = "Veterinar profillari"

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"

    @property
    def has_location(self) -> bool:
        return self.lat is not None and self.lng is not None


class Service(models.Model):
    """Veterinar ko'rsatadigan xizmat (nomi, narxi, davomiyligi)."""

    vet = models.ForeignKey(
        VetProfile, on_delete=models.CASCADE, related_name="services"
    )
    title = models.CharField("Xizmat nomi", max_length=150)
    price = models.DecimalField(
        "Narx", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    duration_min = models.PositiveSmallIntegerField(
        "Davomiyligi (daqiqa)", default=30,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
    )

    class Meta:
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"
        ordering = ["price"]

    def __str__(self):
        return f"{self.title} — {self.price}"
