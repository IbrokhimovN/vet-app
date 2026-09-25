"""
Vet-App Django sozlamalari.

Sozlamalar environ orqali `.env` faylidan o'qiladi (12-faktor uslubi).
Bitta fayl — DEBUG va boshqa qiymatlar muhitga qarab o'zgaradi.
ARCHITECTURE.md hujjatiga muvofiq tuzilgan.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
# Frontend alohida papkada (../frontend). Docker'da backend konteynerida u yo'q —
# u yerda front alohida `frontend` konteynerdan (Caddy) beriladi.
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# --- Muhit o'zgaruvchilari (.env) ---
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
)
# Avval backend/.env, keyin loyiha ildizidagi .env (mavjud bo'lsa). Konteynerda
# muhit o'zgaruvchilari env_file orqali beriladi va fayldan ustun turadi.
for _env_file in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if _env_file.is_file():
        environ.Env.read_env(_env_file)

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Ngrok/Cloudflare kabi tunnel HTTPS'ni HTTP'ga o'girib beradi — shu header
# bo'lmasa, DRF pagination `next`/`previous` havolalarini http:// deb yozadi
# va brauzer https sahifadan uni "mixed content" sifatida bloklaydi.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HTTPS ortida (Caddy) ishlaganda cookie'lar faqat xavfsiz kanal orqali ketadi.
# HTTP'da sinab ko'rilayotganda (COOKIE_SECURE=False) Django admin login ishlashi uchun.
SESSION_COOKIE_SECURE = env.bool("COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("COOKIE_SECURE", default=False)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Ilovalar ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.vets",
    "apps.pets",
    "apps.requests",
    "apps.reviews",
    "apps.notifications",
    "apps.moderation",
    "apps.adminpanel",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.TelegramMiniAppMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIR] if FRONTEND_DIR.is_dir() else [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Ma'lumotlar bazasi (PostgreSQL) ---
# Asosiy DB — PostgreSQL. Qiymatlar .env / .env.docker'dan alohida o'qiladi.
#   Docker:     DB_HOST=db,        DB_PORT=5432
#   Lokal dev:  DB_HOST=localhost, DB_PORT=5433  (Docker DB host porti)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="vetapp"),
        "USER": env("DB_USER", default="vetapp"),
        "PASSWORD": env("DB_PASSWORD", default="vetapp"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5433"),
    }
}

# --- Parol validatorlari ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# --- Maxsus User modeli ---
AUTH_USER_MODEL = "accounts.User"

# --- Til va vaqt ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# --- Statik va media ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").is_dir() else []
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Production'da statik fayllarni Nginx'siz ham to'g'ri (siqilgan, cache-bust
# qilingan) berish uchun — Dockerfile/docker-compose'dagi gunicorn buyrug'i
# bilan birga ishlaydi (7-band: "runserver production uchun mos emas").
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # --- So'rov tezligini cheklash (10-bo'lim: xavfsizlik) ---
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
        # /auth/telegram/ — AllowAny, shuning uchun alohida qattiqroq limit.
        "telegram-auth": "20/min",
        "admin-login": "5/min",
        # So'rov spamiga qarshi (10-bo'lim: pilotda aniqlangan kamchilik) —
        # faqat POST (yaratish)ga tegadi, ro'yxatni ko'rish/yangilashga emas.
        "call-create": "20/day",
        "tender-create": "10/day",
    },
}

# --- JWT ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- CORS (web/mobil mijozlar uchun, 14-bo'lim) ---
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS", default=[])

# --- Test runner (Telegram'ga haqiqiy tarmoq so'rovini oldini oladi) ---
TEST_RUNNER = "config.test_runner.MockedTelegramTestRunner"

# --- Celery (Redis) ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", default=DEBUG)

# --- To'g'ridan chaqiruv (Rejim A) uchun javob muddati ---
# Vet shuncha daqiqa ichida qabul/rad qilmasa, `expire_unanswered_calls` (Celery
# beat, config/celery.py) uni avtomatik "Muddati tugadi"ga o'tkazadi — mijoz
# abadiy kutib qolmasin (10-bo'lim: pilot uchun aniqlangan kamchilik).
CALL_RESPONSE_TIMEOUT_MINUTES = env.int("CALL_RESPONSE_TIMEOUT_MINUTES", default=30)

# --- Telegram botlar (ARCHITECTURE.md: 2 ta bot) ---
TELEGRAM_CLIENT_BOT_TOKEN = env("TELEGRAM_CLIENT_BOT_TOKEN", default="")
TELEGRAM_VET_BOT_TOKEN = env("TELEGRAM_VET_BOT_TOKEN", default="")
# Botlar /start'da ochadigan Mini App manzillari (HTTPS bo'lishi shart — Telegram talabi).
#   Mijoz:  https://<domen>/client/
#   Vet:    https://<domen>/vet/
TELEGRAM_CLIENT_WEBAPP_URL = env("TELEGRAM_CLIENT_WEBAPP_URL", default="")
TELEGRAM_VET_WEBAPP_URL = env("TELEGRAM_VET_WEBAPP_URL", default="")
# initData auth_date shu soniyadan eski bo'lsa rad etiladi (replay himoyasi).
TELEGRAM_AUTH_MAX_AGE = env.int("TELEGRAM_AUTH_MAX_AGE", default=86400)

# --- Qo'llab-quvvatlash (10-bo'lim: pilot uchun aniqlangan kamchilik) ---
# Mijoz/vet ilovasidagi "Yordam markazi" shu Telegram hisobga ulanadi.
# "@" belgisisiz yoziladi, masalan: SUPPORT_TELEGRAM_USERNAME=vetapp_support
# Bo'sh qoldirilsa, front "hozircha ulanmagan" degan xabar ko'rsatadi (kodga
# qattiq yozilgan soxta havola o'rniga) — /api/v1/config/ orqali o'qiladi.
SUPPORT_TELEGRAM_USERNAME = env("SUPPORT_TELEGRAM_USERNAME", default="")

# --- Xatolik kuzatuvi (10-bo'lim: pilot uchun aniqlangan kamchilik) ---
# SENTRY_DSN bo'sh bo'lsa — hech narsa ulanmaydi, oddiy logging'ga tushadi.
# sentry.io'da bepul loyiha ochib, DSN'ni .env.prod'ga qo'ying — shu bilan darhol
# faollashadi (kodni qayta joylashtirish shart emas).
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            # WARNING+ darajadagi log yozuvlari ham Sentry'ga boradi (masalan,
            # notifications/tasks.py'dagi "bildirishnoma butunlay muvaffaqiyatsiz").
            LoggingIntegration(level=None, event_level="WARNING"),
        ],
        environment="production" if not DEBUG else "development",
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        # Telefon raqami, ism kabi shaxsiy ma'lumotlar Sentry'ga yuborilmasin.
        send_default_pii=False,
    )
