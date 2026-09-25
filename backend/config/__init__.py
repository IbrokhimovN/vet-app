"""config paketi — Django sozlamalari va Celery ilovasi."""
from .celery import app as celery_app

__all__ = ("celery_app",)
