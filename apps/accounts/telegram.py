"""
Telegram WebApp initData tekshirish (ARCHITECTURE.md 3.1–3.2).

Telegram Mini App `initData` ni imzolangan holda beradi. Uni bot token bilan
HMAC-SHA256 orqali tekshiramiz — bu parolsiz, ishonchli autentifikatsiya.

Algoritm (Telegram rasmiy spetsifikatsiyasi):
    secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
    data_check_string = hash'dan tashqari maydonlar, alfavit tartibida "k=v\\n"
    calculated_hash = HMAC_SHA256(key=secret_key, msg=data_check_string)
    calculated_hash == initData.hash  bo'lsa -> haqiqiy
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class TelegramAuthError(Exception):
    """initData tekshiruvi muvaffaqiyatsiz bo'lganda ko'tariladi."""


def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    """
    initData satrini tekshiradi va ichidagi `user` ma'lumotini qaytaradi.

    :param init_data: Telegram WebApp bergan xom initData satri (query-string).
    :param bot_token: Tegishli botning tokeni (mijoz yoki vet boti).
    :param max_age: auth_date shu soniyadan eski bo'lsa rad etiladi (replay himoyasi).
    :return: Telegram user dict — {id, first_name, last_name, username, ...}.
    :raises TelegramAuthError: imzo soxta, eskirgan yoki maydonlar yetishmasa.
    """
    if not init_data:
        raise TelegramAuthError("initData bo'sh.")
    if not bot_token:
        raise TelegramAuthError("Bot tokeni sozlanmagan.")

    # parse_qsl percent-decode qiladi va tartibni saqlaydi.
    pairs = dict(parse_qsl(init_data, strict_parsing=False))

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("initData ichida hash yo'q.")

    # data_check_string — qolgan maydonlar alfavit tartibida "key=value\n".
    data_check_string = "\n".join(
        f"{key}={pairs[key]}" for key in sorted(pairs)
    )

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    # Doimiy vaqtli solishtirish (timing-attack himoyasi).
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("Imzo noto'g'ri — soxta initData.")

    # auth_date eskirganini tekshirish.
    auth_date = pairs.get("auth_date")
    if not auth_date or not auth_date.isdigit():
        raise TelegramAuthError("auth_date yo'q yoki noto'g'ri.")
    if max_age and (time.time() - int(auth_date)) > max_age:
        raise TelegramAuthError("initData eskirgan — qaytadan kiring.")

    # user maydoni — JSON ko'rinishida.
    user_raw = pairs.get("user")
    if not user_raw:
        raise TelegramAuthError("initData ichida user ma'lumoti yo'q.")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise TelegramAuthError("user JSON xato.") from exc

    if not user.get("id"):
        raise TelegramAuthError("Telegram user id yo'q.")

    return user
