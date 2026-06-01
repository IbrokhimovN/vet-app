"""
Telegram autentifikatsiyasi biznes-mantig'i (ARCHITECTURE.md 3.1).

initData tekshirilgach, Telegram user ma'lumotidan tizim User'ini topadi yoki
yaratadi va kirish usulini (AuthIdentity) qayd etadi.
"""
from django.db import transaction

from .models import AuthIdentity, AuthProvider, Role, User

# Qaysi bot orqali kirgani rolni belgilaydi (ARCHITECTURE.md: 2 ta bot).
APP_ROLE = {
    "client": Role.CLIENT,
    "vet": Role.VET,
}


@transaction.atomic
def get_or_create_telegram_user(tg_user: dict, app: str) -> tuple[User, bool]:
    """
    Telegram user dict va app turiga ko'ra User topadi yoki yaratadi.

    :param tg_user: validate_init_data qaytargan dict (id, first_name, ...).
    :param app: "client" yoki "vet" — qaysi Mini App orqali kirilgani.
    :return: (user, created) — user obyekti va yangi yaratildimi.

    Eslatma: mavjud foydalanuvchining roli o'zgartirilmaydi (vet profilini
    tasodifan yo'qotmaslik uchun). Rol faqat birinchi yaratilishda o'rnatiladi.
    """
    telegram_id = tg_user["id"]
    role = APP_ROLE.get(app, Role.CLIENT)

    defaults = {
        "role": role,
        "first_name": tg_user.get("first_name", ""),
        "last_name": tg_user.get("last_name", ""),
        "username": tg_user.get("username") or f"tg_{telegram_id}",
        "language": _normalize_language(tg_user.get("language_code")),
        "photo_url": tg_user.get("photo_url", ""),
    }

    user, created = User.objects.get_or_create(
        telegram_id=telegram_id, defaults=defaults
    )

    if not created:
        # Mavjud user — Telegram profilidagi o'zgarishlarni yangilab qo'yamiz
        # (rol bundan mustasno — u o'zgarmaydi).
        user.first_name = tg_user.get("first_name", user.first_name)
        user.last_name = tg_user.get("last_name", user.last_name)
        if tg_user.get("photo_url"):
            user.photo_url = tg_user["photo_url"]
        user.save(update_fields=["first_name", "last_name", "photo_url"])

    AuthIdentity.objects.get_or_create(
        provider=AuthProvider.TELEGRAM,
        external_id=str(telegram_id),
        defaults={"user": user, "is_verified": True},
    )

    return user, created


def _normalize_language(code: str | None) -> str:
    """Telegram language_code ('uz', 'ru', 'en'...) ni qo'llab-quvvatlanadiganga moslaydi."""
    if code and code.lower().startswith("ru"):
        return "ru"
    return "uz"
