"""
Bildirishnoma testlari (6-bosqich).

Tekshiriladi: hodisalarda Notification yozuvi yaratiladi, to'g'ri qabul
qiluvchi/bot tanlanadi, tender fan-out mos vetlarga boradi, va ilova ichidagi
lenta API'si ishlaydi. Telegram'ga real so'rov yo'q (token bo'sh -> faqat yozuv).
"""
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.pets.models import Pet
from apps.requests.models import Offer, OfferStatus, ServiceRequest, ServiceStatus
from apps.vets.models import Specialization, VetProfile

from .models import Notification, NotificationKind


class Base(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create(username="cli", telegram_id=10, role=Role.CLIENT)
        self.vet_user = User.objects.create(username="vet", telegram_id=20, role=Role.VET, first_name="Dr")
        self.vet = VetProfile.objects.create(user=self.vet_user, city="Toshkent", is_available=True)
        self.spec = Specialization.objects.create(name="Test-It", slug="ti", icon="🐕")
        self.vet.specializations.add(self.spec)
        self.pet = Pet.objects.create(owner=self.client_user, name="Rex", species="It")


# ============================ REJIM A ============================

class CallNotificationTests(Base):
    def test_new_call_notifies_vet_via_vet_bot(self):
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(
            reverse("v1:call-list"),
            {"vet": self.vet.id, "pet": self.pet.id, "type": "home"}, format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        n = Notification.objects.get(recipient=self.vet_user)
        self.assertEqual(n.kind, NotificationKind.CALL_NEW)
        self.assertEqual(n.bot, "vet")
        # mijozga emas, faqat vetga
        self.assertFalse(Notification.objects.filter(recipient=self.client_user).exists())

    def test_status_change_notifies_client(self):
        self.client.force_authenticate(self.client_user)
        call_id = self.client.post(
            reverse("v1:call-list"),
            {"vet": self.vet.id, "type": "online"}, format="json",
        ).json()["id"]
        Notification.objects.all().delete()  # yaratilish xabarini tozalaymiz

        self.client.force_authenticate(self.vet_user)
        self.client.post(reverse("v1:call-action", args=[call_id, "accept"]))
        n = Notification.objects.get(recipient=self.client_user)
        self.assertEqual(n.kind, NotificationKind.CALL_STATUS)
        self.assertEqual(n.bot, "client")

    def test_client_cancel_notifies_vet(self):
        self.client.force_authenticate(self.client_user)
        call_id = self.client.post(
            reverse("v1:call-list"),
            {"vet": self.vet.id, "type": "online"}, format="json",
        ).json()["id"]
        Notification.objects.all().delete()

        self.client.post(reverse("v1:call-action", args=[call_id, "cancel"]))
        n = Notification.objects.get(recipient=self.vet_user)
        self.assertEqual(n.kind, NotificationKind.CALL_STATUS)
        self.assertEqual(n.bot, "vet")


# ============================ REJIM B ============================

class TenderNotificationTests(Base):
    def _make_tender(self):
        self.client.force_authenticate(self.client_user)
        return self.client.post(
            reverse("v1:sr-list"),
            {"type": "home", "specialization": self.spec.id, "city": "Toshkent"},
            format="json",
        ).json()["id"]

    def test_new_tender_fans_out_to_matching_vet(self):
        self._make_tender()
        n = Notification.objects.filter(recipient=self.vet_user, kind=NotificationKind.TENDER_NEW)
        self.assertEqual(n.count(), 1)
        self.assertEqual(n.first().bot, "vet")

    def test_tender_skips_unavailable_or_other_spec(self):
        # boshqa mutaxassislik
        other = Specialization.objects.create(name="Test-Mushuk", slug="tm")
        v2 = User.objects.create(username="v2", telegram_id=21, role=Role.VET)
        VetProfile.objects.create(user=v2, is_available=True).specializations.add(other)
        # bo'sh emas vet (mos spec lekin band)
        v3 = User.objects.create(username="v3", telegram_id=22, role=Role.VET)
        VetProfile.objects.create(user=v3, is_available=False).specializations.add(self.spec)

        self._make_tender()
        self.assertEqual(Notification.objects.filter(recipient=v2).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=v3).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.vet_user).count(), 1)

    def test_new_offer_notifies_client(self):
        sr_id = self._make_tender()
        Notification.objects.all().delete()
        self.client.force_authenticate(self.vet_user)
        self.client.post(
            reverse("v1:sr-offer-create", args=[sr_id]), {"price": "150000"}, format="json"
        )
        n = Notification.objects.get(recipient=self.client_user)
        self.assertEqual(n.kind, NotificationKind.OFFER_NEW)
        self.assertEqual(n.bot, "client")

    def test_accept_notifies_winner_and_losers(self):
        sr = ServiceRequest.objects.create(
            client=self.client_user, specialization=self.spec, type="home",
            status=ServiceStatus.OPEN,
        )
        v2 = User.objects.create(username="v2", telegram_id=23, role=Role.VET)
        vp2 = VetProfile.objects.create(user=v2)
        o1 = Offer.objects.create(request=sr, vet=self.vet, price=100, status=OfferStatus.SENT)
        Offer.objects.create(request=sr, vet=vp2, price=200, status=OfferStatus.SENT)
        Notification.objects.all().delete()

        self.client.force_authenticate(self.client_user)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(reverse("v1:offer-accept", args=[o1.id]))
        self.assertEqual(resp.status_code, 200, resp.content)

        win = Notification.objects.get(recipient=self.vet_user)
        self.assertEqual(win.kind, NotificationKind.OFFER_ACCEPTED)
        lose = Notification.objects.get(recipient=v2)
        self.assertEqual(lose.kind, NotificationKind.OFFER_DECLINED)


# ============================ Ilova ichidagi lenta ============================

class NotificationFeedTests(Base):
    def setUp(self):
        super().setUp()
        Notification.objects.create(
            recipient=self.vet_user, kind=NotificationKind.CALL_NEW,
            title="A", body="x", bot="vet",
        )
        Notification.objects.create(
            recipient=self.vet_user, kind=NotificationKind.TENDER_NEW,
            title="B", body="y", bot="vet", is_read=True,
        )

    def test_list_and_unread_count(self):
        self.client.force_authenticate(self.vet_user)
        resp = self.client.get(reverse("v1:notification-list"))
        self.assertEqual(resp.json()["count"], 2)

        unread = self.client.get(reverse("v1:notification-unread"))
        self.assertEqual(unread.json()["unread"], 1)

        only_unread = self.client.get(reverse("v1:notification-list"), {"unread": "1"})
        self.assertEqual(only_unread.json()["count"], 1)

    def test_mark_all_read(self):
        self.client.force_authenticate(self.vet_user)
        resp = self.client.post(reverse("v1:notification-read-all"))
        self.assertEqual(resp.json()["updated"], 1)
        self.assertEqual(
            Notification.objects.filter(recipient=self.vet_user, is_read=False).count(), 0
        )

    def test_user_sees_only_own(self):
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:notification-list"))
        self.assertEqual(resp.json()["count"], 0)


# ============================ Yetkazish (Telegram) ============================

@override_settings(TELEGRAM_VET_BOT_TOKEN="TEST:TOKEN")
class DeliveryTests(Base):
    @patch("apps.notifications.telegram.requests.post")
    def test_delivery_marks_sent(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True, "result": {"message_id": 7}}

        self.client.force_authenticate(self.client_user)
        self.client.post(
            reverse("v1:call-list"),
            {"vet": self.vet.id, "type": "online"}, format="json",
        )
        n = Notification.objects.get(recipient=self.vet_user)
        self.assertTrue(n.is_sent)
        self.assertIsNotNone(n.sent_at)
        self.assertEqual(n.error, "")
        # Telegram API chaqirildi va chat_id = vet telegram_id
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["chat_id"], self.vet_user.telegram_id)
