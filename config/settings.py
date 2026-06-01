"""
Vet-App Django sozlamalari.

Sozlamalar environ orqali `.env` faylidan o'qiladi (12-faktor uslubi).
Bitta fayl — DEBUG va boshqa qiymatlar muhitga qarab o'zgaradi.
ARCHITECTURE.md hujjatiga muvofiq tuzilgan.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Muhit o'zgaruvchilari (.env) ---
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    CORS_ALLOW_ALL_ORIGINS=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

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
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [BASE_DIR / "frontend"],
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
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

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

# --- Celery (Redis) ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", default=DEBUG)

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
