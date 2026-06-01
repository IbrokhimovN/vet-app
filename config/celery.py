"""Celery ilovasi — asinxron bildirishnomalar uchun (ARCHITECTURE.md 7-bo'lim)."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("vet_app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
