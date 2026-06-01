"""
Mijoz boti — uy hayvoni egalari uchun.

/start bosilganda kutib oladi va mijoz Mini App'ini ochadigan tugma beradi.
Ishga tushirish:  python -m bots.client_bot
"""
import sys

from bots import _bootstrap  # noqa: F401  (Django settings yuklanadi)
from bots.base import TelegramBot, webapp_button
from django.conf import settings

OPEN_TEXT = "🐾 Veterinar topish"

WELCOME = (
    "<b>Vet-App'ga xush kelibsiz!</b> 🐾\n\n"
    "Bu yerda yaqin atrofdagi veterinarlarni topasiz, ularning narxlari va "
    "baholarini ko'rasiz, to'g'ridan-to'g'ri chaqiruv yoki e'lon (tender) "
    "joylashtirasiz.\n\n"
    "Boshlash uchun pastdagi tugmani bosing 👇"
)

HELP = (
    "Quyidagi tugma orqali Mini App'ni oching. "
    "Veterinar qidirish, chaqiruv yuborish va izoh qoldirish — barchasi o'sha yerda.\n\n"
    "/start — ilovani ochish"
)


def build() -> TelegramBot:
    token = settings.TELEGRAM_CLIENT_BOT_TOKEN
    url = settings.TELEGRAM_CLIENT_WEBAPP_URL
    if not token:
        sys.exit("TELEGRAM_CLIENT_BOT_TOKEN sozlanmagan (.env).")
    if not url:
        sys.exit("TELEGRAM_CLIENT_WEBAPP_URL sozlanmagan (.env). HTTPS manzil kerak.")

    bot = TelegramBot(token, name="client")
    keyboard = webapp_button(OPEN_TEXT, url)

    @bot.command("start")
    def start(b, msg):
        b.send_message(msg["chat"]["id"], WELCOME, reply_markup=keyboard)

    @bot.command("help")
    def help_(b, msg):
        b.send_message(msg["chat"]["id"], HELP, reply_markup=keyboard)

    @bot.default
    def fallback(b, msg):
        b.send_message(msg["chat"]["id"], HELP, reply_markup=keyboard)

    # Chat menyusi tugmasi ham Mini App'ni ochsin (xato bo'lsa ham bot ishlaydi).
    try:
        bot.set_menu_button(OPEN_TEXT, url)
    except Exception:
        pass
    return bot


if __name__ == "__main__":
    build().run()
