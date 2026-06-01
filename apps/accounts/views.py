"""
Auth view'lari (ARCHITECTURE.md 3.1, 6.1).

POST /api/v1/auth/telegram/ — initData -> JWT (access + refresh).
GET  /api/v1/auth/me/        — joriy foydalanuvchi.
(refresh uchun SimpleJWT'ning TokenRefreshView ishlatiladi — urls.py'da.)
"""
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import TelegramAuthSerializer, UserSerializer
from .services import get_or_create_telegram_user
from .telegram import TelegramAuthError, validate_init_data


def _bot_token(app: str) -> str:
    """Mini App turiga mos bot tokenini (so'rov vaqtida) qaytaradi."""
    return {
        "client": settings.TELEGRAM_CLIENT_BOT_TOKEN,
        "vet": settings.TELEGRAM_VET_BOT_TOKEN,
    }.get(app, "")


class TelegramAuthView(APIView):
    """initData ni tekshirib, JWT qaytaradi."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = serializer.validated_data["app"]
        init_data = serializer.validated_data["init_data"]

        try:
            tg_user = validate_init_data(
                init_data,
                bot_token=_bot_token(app),
                max_age=settings.TELEGRAM_AUTH_MAX_AGE,
            )
        except TelegramAuthError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED
            )

        user, created = get_or_create_telegram_user(tg_user, app)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "created": created,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """Joriy foydalanuvchi ma'lumotini qaytaradi / yangilaydi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
