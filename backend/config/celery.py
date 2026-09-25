"""Celery ilovasi — asinxron bildirishnomalar uchun (ARCHITECTURE.md 7-bo'lim)."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("vet_app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Davriy vazifalar (`celery -A config beat` orqali ishga tushiriladi — alohida
# konteyner/jarayon, docker-compose.yml'dagi `beat` xizmati).
app.conf.beat_schedule = {
    "expire-unanswered-calls": {
        "task": "apps.requests.tasks.expire_unanswered_calls",
        "schedule": 300.0,  # har 5 daqiqada
    },
}
