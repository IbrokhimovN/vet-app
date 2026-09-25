"""
Telegram auth testlari (ARCHITECTURE.md 3-bo'lim).

Haqiqiy initData imzosini yasab, oqimni uchidan-uchiga tekshiradi.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Role, User

FAKE_TOKEN = "123456:TEST-BOT-TOKEN"


def make_init_data(token: str, user: dict, auth_date: int | None = None) -> str:
    """Berilgan token bilan haqiqiy imzolangan initData satrini yasaydi."""
    if auth_date is None:
        auth_date = int(time.time())
    fields = {
        "auth_date": str(auth_date),
        "query_id": "AAH-test",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(
        secret, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(fields)


@override_settings(
    TELEGRAM_VET_BOT_TOKEN=FAKE_TOKEN,
    TELEGRAM_CLIENT_BOT_TOKEN=FAKE_TOKEN,
)
class TelegramAuthTests(TestCase):
    def setUp(self):
        self.url = reverse("v1:telegram-auth")
        self.tg_user = {
            "id": 555000111,
            "first_name": "Ali",
            "last_name": "Valiyev",
            "username": "ali_v",
            "language_code": "uz",
        }

    def test_valid_initdata_creates_vet_and_returns_jwt(self):
        init_data = make_init_data(FAKE_TOKEN, self.tg_user)
        resp = self.client.post(
            self.url, {"init_data": init_data, "app": "vet"}
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertTrue(body["created"])
        self.assertEqual(body["user"]["role"], Role.VET)

        user = User.objects.get(telegram_id=self.tg_user["id"])
        self.assertEqual(user.role, Role.VET)
        self.assertTrue(user.identities.filter(provider="telegram").exists())

    def test_client_app_sets_client_role(self):
        init_data = make_init_data(FAKE_TOKEN, self.tg_user)
        resp = self.client.post(
            self.url, {"init_data": init_data, "app": "client"}
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["user"]["role"], Role.CLIENT)

    def test_tampered_hash_rejected(self):
        init_data = make_init_data(FAKE_TOKEN, self.tg_user)
        tampered = init_data[:-4] + "0000"  # hash oxirini buzamiz
        resp = self.client.post(
            self.url, {"init_data": tampered, "app": "vet"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_wrong_bot_token_rejected(self):
        # initData mijoz boti tokeni bilan imzolangan, lekin boshqa token bilan
        # tekshiriladi -> imzo mos kelmaydi.
        init_data = make_init_data("999:OTHER-TOKEN", self.tg_user)
        resp = self.client.post(
            self.url, {"init_data": init_data, "app": "vet"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_expired_initdata_rejected(self):
        old = int(time.time()) - 100000  # max_age (86400) dan eski
        init_data = make_init_data(FAKE_TOKEN, self.tg_user, auth_date=old)
        resp = self.client.post(
            self.url, {"init_data": init_data, "app": "vet"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_me_endpoint_with_jwt(self):
        init_data = make_init_data(FAKE_TOKEN, self.tg_user)
        auth = self.client.post(
            self.url, {"init_data": init_data, "app": "vet"}
        ).json()
        me_url = reverse("v1:me")
        resp = self.client.get(
            me_url, HTTP_AUTHORIZATION=f"Bearer {auth['access']}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["telegram_id"], self.tg_user["id"])

    def test_me_requires_auth(self):
        resp = self.client.get(reverse("v1:me"))
        self.assertEqual(resp.status_code, 401)

    def test_client_saves_home_location(self):
        init_data = make_init_data(FAKE_TOKEN, self.tg_user)
        auth = self.client.post(self.url, {"init_data": init_data, "app": "client"}).json()
        resp = self.client.patch(
            reverse("v1:me"),
            data=json.dumps({"city": "Andijon viloyati", "district": "Asaka", "lat": 40.75, "lng": 72.03}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {auth['access']}",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["city"], "Andijon viloyati")
        self.assertEqual(resp.json()["lat"], 40.75)


class PublicConfigTests(TestCase):
    def test_config_accessible_without_auth(self):
        resp = self.client.get(reverse("v1:public-config"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("support_telegram_username", resp.json())

    @override_settings(SUPPORT_TELEGRAM_USERNAME="vetapp_support")
    def test_config_returns_configured_value(self):
        resp = self.client.get(reverse("v1:public-config"))
        self.assertEqual(resp.json()["support_telegram_username"], "vetapp_support")
