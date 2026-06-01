"""
Veterinar boti — vetlar uchun alohida bot.

/start bosilganda kutib oladi va vet Mini App'ini (kabinet) ochadigan tugma beradi.
Ishga tushirish:  python -m bots.vet_bot
"""
import sys

from bots import _bootstrap  # noqa: F401  (Django settings yuklanadi)
from bots.base import TelegramBot, webapp_button
from django.conf import settings

OPEN_TEXT = "🩺 Kabinetni ochish"

WELCOME = (
    "<b>Vet-App — veterinarlar uchun.</b> 🩺\n\n"
    "Profilingizni to'ldiring, xizmat va narxlaringizni qo'ying, kelgan "
    "chaqiruvlar hamda e'lonlarni (tenderlar) ko'rib, takliflar yuboring.\n\n"
    "Kabinetga kirish uchun pastdagi tugmani bosing 👇"
)

HELP = (
    "Quyidagi tugma orqali kabinetni oching. "
    "Profil, xizmatlar, chaqiruvlar va takliflar — barchasi o'sha yerda.\n\n"
    "/start — kabinetni ochish"
)


def build() -> TelegramBot:
    token = settings.TELEGRAM_VET_BOT_TOKEN
    url = settings.TELEGRAM_VET_WEBAPP_URL
    if not token:
        sys.exit("TELEGRAM_VET_BOT_TOKEN sozlanmagan (.env).")
    if not url:
        sys.exit("TELEGRAM_VET_WEBAPP_URL sozlanmagan (.env). HTTPS manzil kerak.")

    bot = TelegramBot(token, name="vet")
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

    # Chat menyusi tugmasi ham kabinetni ochsin (xato bo'lsa ham bot ishlaydi).
    try:
        bot.set_menu_button(OPEN_TEXT, url)
    except Exception:
        pass
    return bot


if __name__ == "__main__":
    build().run()
