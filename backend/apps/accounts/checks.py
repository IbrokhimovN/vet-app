"""Production xavfsizligi bo'yicha startup tekshiruvlari (ARCHITECTURE.md 10-bo'lim).

`manage.py check --deploy` yoki DEBUG=False bilan ishga tushirilganda,
.env'da SECRET_KEY o'rnatilmagan bo'lsa, sukut bo'yicha noto'g'ri qiymat
ishlatilib ketmasligi uchun qattiq xato beradi.
"""
from django.conf import settings
from django.core.checks import Error, register

INSECURE_SECRET_KEY = "dev-insecure-change-me"


@register()
def check_secret_key_in_production(app_configs, **kwargs):
    errors = []
    if not settings.DEBUG and settings.SECRET_KEY == INSECURE_SECRET_KEY:
        errors.append(
            Error(
                "SECRET_KEY .env faylida o'rnatilmagan (sukut qiymat ishlatilmoqda).",
                hint="DEBUG=False bilan production'da .env ga tasodifiy SECRET_KEY qo'ying.",
                id="accounts.E001",
            )
        )
    return errors
