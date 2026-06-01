from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reviews"
    verbose_name = "Izohlar"

    def ready(self):
        from . import signals  # noqa: F401  (signal'larni ulash)
