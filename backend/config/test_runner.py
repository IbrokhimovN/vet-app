"""
Test runner — Telegram Bot API'ga haqiqiy tarmoq so'rovlarini oldini oladi.

Bildirishnoma vazifalari testlarda sinxron (eager) bajariladi va `apps.notifications.telegram.send_message` chaqiriladi. Buni
mock qilmasak, har bir test ishga tushirilishida haqiqiy `api.telegram.org`ga
so'rov ketadi — sekin, tarmoqqa bog'liq va CI'da ishonchsiz.
"""
from unittest import mock

from django.test import override_settings
from django.test.runner import DiscoverRunner


class MockedTelegramTestRunner(DiscoverRunner):
    """
    Butun test sessiyasi davomida haqiqiy `requests.post` chaqiruvini muvaffaqiyatli
    javob bilan almashtiradi. Pastki darajada (HTTP chaqiruvning o'zi) patch qilingani
    uchun `apps/notifications/tests.py`dagi o'ziga xos `@patch(".../requests.post")`
    testlari bu bilan to'qnashmaydi — ular o'z davrida ustidan yozib ishlaydi.
    """

    def run_tests(self, *args, **kwargs):
        # Testlar muhitga bog'liq bo'lmasin: prod muhitda (CELERY_TASK_ALWAYS_EAGER=False,
        # Redis broker) ham vazifalar sinxron bajarilsin.
        fake_response = mock.Mock()
        fake_response.json.return_value = {"ok": True, "result": {"message_id": 0}}
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True), mock.patch(
            "apps.notifications.telegram.requests.post",
            return_value=fake_response,
        ):
            return super().run_tests(*args, **kwargs)
