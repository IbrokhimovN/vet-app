"""
Oddiy long-polling Telegram bot bazasi (qo'shimcha kutubxonasiz — `requests`).

Ikkala bot ham (mijoz, vet) shu `TelegramBot` ustiga quriladi. Vazifasi yengil:
foydalanuvchini kutib olish va Mini App'ni ochadigan tugma berish. Asosiy biznes
mantiq API'da, shuning uchun bot ataylab sodda saqlangan.
"""
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("bots")

API_URL = "https://api.telegram.org/bot{token}/{method}"
POLL_TIMEOUT = 30          # Telegram long-poll soniyasi
HTTP_TIMEOUT = POLL_TIMEOUT + 15

# getUpdates offset shu yerga yoziladi — jarayon qayta ishga tushganda eski
# xabarlar qayta ishlanmasligi (yoki yo'qolmasligi) uchun (8-band: kamchilik).
OFFSET_DIR = Path(__file__).resolve().parent.parent / ".offsets"


class BotError(Exception):
    """Telegram API rad etdi yoki tarmoq xatosi."""


def webapp_button(text: str, url: str) -> dict:
    """Mini App'ni ochadigan inline tugma (reply_markup uchun)."""
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": url}}]]}


class TelegramBot:
    def __init__(self, token: str, name: str = "bot"):
        self.token = token
        self.name = name
        self._offset_file = OFFSET_DIR / f"{name}.offset"
        self._offset = self._load_offset()
        self._handlers = {}          # buyruq nomi -> funksiya(bot, message)
        self._default = None         # buyruqsiz xabarlar uchun

    # --- offsetni saqlash (qayta ishga tushirilganda xabar yo'qolmasin) ---
    def _load_offset(self):
        try:
            return int(self._offset_file.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None

    def _save_offset(self):
        OFFSET_DIR.mkdir(parents=True, exist_ok=True)
        self._offset_file.write_text(str(self._offset))

    # --- handlerlarni ro'yxatdan o'tkazish ---
    def command(self, name: str):
        """`@bot.command("start")` dekoratori."""
        def deco(fn):
            self._handlers[name] = fn
            return fn
        return deco

    def default(self, fn):
        """Buyruq bo'lmagan har qanday xabar uchun handler."""
        self._default = fn
        return fn

    # --- Telegram API ---
    def _call(self, method: str, _timeout=HTTP_TIMEOUT, **params):
        url = API_URL.format(token=self.token, method=method)
        try:
            resp = requests.post(url, json=params, timeout=_timeout)
        except requests.RequestException as exc:
            raise BotError(str(exc)) from exc
        data = resp.json()
        if not data.get("ok"):
            raise BotError(data.get("description", "Telegram API xatosi"))
        return data["result"]

    def send_message(self, chat_id, text: str, reply_markup: dict = None) -> int:
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            params["reply_markup"] = reply_markup
        return self._call("sendMessage", **params)["message_id"]

    def set_menu_button(self, text: str, url: str):
        """Chat menyusi tugmasini Mini App'ga ulaydi (barcha foydalanuvchilar uchun)."""
        self._call(
            "setChatMenuButton",
            menu_button={"type": "web_app", "text": text, "web_app": {"url": url}},
        )

    # --- update oqimi ---
    def _get_updates(self):
        params = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
        if self._offset is not None:
            params["offset"] = self._offset
        return self._call("getUpdates", **params)

    def _dispatch(self, update: dict):
        msg = update.get("message")
        if not msg or "text" not in msg:
            return
        text = msg["text"].strip()
        if text.startswith("/"):
            cmd = text[1:].split()[0].split("@")[0].lower()
            handler = self._handlers.get(cmd)
            if handler:
                handler(self, msg)
                return
        if self._default:
            self._default(self, msg)

    def run(self):
        """Long-polling tsikli (Ctrl+C bilan to'xtaydi)."""
        me = self._call("getMe", _timeout=HTTP_TIMEOUT)
        logger.info("[%s] @%s ishga tushdi (long polling)", self.name, me.get("username"))
        while True:
            try:
                updates = self._get_updates()
            except BotError as exc:
                logger.warning("[%s] getUpdates xato: %s — 3s kutib qayta urinaman", self.name, exc)
                time.sleep(3)
                continue
            for upd in updates:
                self._offset = upd["update_id"] + 1
                try:
                    self._dispatch(upd)
                except Exception:  # bitta xabar butun botni yiqitmasin
                    logger.exception("[%s] xabarni qayta ishlashda xato", self.name)
                finally:
                    self._save_offset()
