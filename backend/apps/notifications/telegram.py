"""
Telegram Bot API orqali xabar yuborish (ARCHITECTURE.md 7-bo'lim).

Qaysi bot orqali yuborish qabul qiluvchining roliga bog'liq:
  - mijoz  -> CLIENT bot (u shu botni ishga tushirgan)
  - vet    -> VET bot

Tokenlar so'rov vaqtida `settings`'dan o'qiladi (test'da override mumkin).
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT = 10


class TelegramSendError(Exception):
    """Telegram'ga xabar yuborib bo'lmadi."""


def bot_token(bot: str) -> str:
    """`bot` = "vet" | "client" uchun mos token."""
    if bot == "vet":
        return settings.TELEGRAM_VET_BOT_TOKEN
    return settings.TELEGRAM_CLIENT_BOT_TOKEN


def send_message(bot: str, chat_id, text: str) -> int:
    """
    Telegram chatga matn yuboradi, message_id qaytaradi.
    Xatolikda TelegramSendError ko'taradi (token yo'q / API rad etdi).
    """
    token = bot_token(bot)
    if not token:
        raise TelegramSendError(f"'{bot}' bot tokeni sozlanmagan.")

    try:
        resp = requests.post(
            API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:  # tarmoq xatosi
        raise TelegramSendError(str(exc)) from exc

    data = resp.json()
    if not data.get("ok"):
        raise TelegramSendError(data.get("description", "Telegram API xatosi"))
    return data["result"]["message_id"]
