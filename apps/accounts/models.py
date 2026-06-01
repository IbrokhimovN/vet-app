"""
Foydalanuvchi modellari (ARCHITECTURE.md 4-bo'lim va 14-bo'lim).

User — maxsus foydalanuvchi modeli. `telegram_id` null bo'lishi mumkin, chunki
kelajakda web/mobil orqali Telegramsiz foydalanuvchi ham mavjud bo'la oladi.
AuthIdentity — bitta User'ga bir nechta kirish usulini bog'laydi (telegram/phone/email).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    CLIENT = "client", "Mijoz"
    VET = "vet", "Veterinar"
    ADMIN = "admin", "Administrator"


class Language(models.TextChoices):
    UZ = "uz", "O'zbekcha"
    RU = "ru", "Ruscha"


class User(AbstractUser):
    """Maxsus foydalanuvchi. Telegram orqali yoki (kelajak) web/mobil orqali kiradi."""

    telegram_id = models.BigIntegerField(
        "Telegram ID", unique=True, null=True, blank=True, db_index=True
    )
    role = models.CharField(
        "Rol", max_length=10, choices=Role.choices, default=Role.CLIENT
    )
    phone = models.CharField("Telefon", max_length=20, blank=True)
    language = models.CharField(
        "Til", max_length=2, choices=Language.choices, default=Language.UZ
    )
    photo_url = models.URLField("Rasm havolasi", blank=True)

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self):
        label = self.get_full_name() or self.username
        return f"{label} ({self.get_role_display()})"

    @property
    def is_vet(self):
        return self.role == Role.VET

    @property
    def is_client(self):
        return self.role == Role.CLIENT


class AuthProvider(models.TextChoices):
    TELEGRAM = "telegram", "Telegram"
    PHONE = "phone", "Telefon (OTP)"
    EMAIL = "email", "Email"


class AuthIdentity(models.Model):
    """
    Foydalanuvchining kirish usuli. Bir User'da bir nechta bo'lishi mumkin.
    MVP'da faqat provider=telegram ishlatiladi; qolganlari kelajak uchun zaxira.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="identities"
    )
    provider = models.CharField(
        "Provayder", max_length=10, choices=AuthProvider.choices
    )
    external_id = models.CharField("Tashqi ID", max_length=128)
    is_verified = models.BooleanField("Tasdiqlangan", default=False)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Kirish usuli"
        verbose_name_plural = "Kirish usullari"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                name="unique_provider_external_id",
            )
        ]

    def __str__(self):
        return f"{self.get_provider_display()}: {self.external_id}"
