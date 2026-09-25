"""Auth API marshrutlari (ARCHITECTURE.md 6.1)."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import MeView, PublicConfigView, TelegramAuthView

urlpatterns = [
    path("telegram/", TelegramAuthView.as_view(), name="telegram-auth"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("config/", PublicConfigView.as_view(), name="public-config"),
]
