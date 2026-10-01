"""requests testlari — REJIM A (chaqiruv) va REJIM B (tender)."""
from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.pets.models import Pet
from apps.vets.models import Specialization, VetProfile

from .models import CallRequest, CallStatus, Offer, OfferStatus, ServiceRequest, ServiceStatus
from .tasks import expire_unanswered_calls


class Base(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create(username="cli", telegram_id=1, role=Role.CLIENT, phone="+998901112233")
        self.vet_user = User.objects.create(username="vet", telegram_id=2, role=Role.VET, first_name="Dr", phone="+998904445566")
        self.vet = VetProfile.objects.create(user=self.vet_user, city="Toshkent")
        self.spec = Specialization.objects.create(name="Test-It", slug="ti", icon="🐕")
        self.vet.specializations.add(self.spec)
        self.pet = Pet.objects.create(owner=self.client_user, name="Rex", species="It")


# ============================ REJIM A ============================

class CallRequestTests(Base):
    def _create(self):
        self.client.force_authenticate(self.client_user)
        return self.client.post(
            reverse("v1:call-list"),
            {"vet": self.vet.id, "pet": self.pet.id, "type": "home", "address": "Uy"},
            format="json",
        )

    def test_client_creates_call(self):
        resp = self._create()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["status"], CallStatus.PENDING)
        self.assertEqual(resp.json()["vet_info"]["full_name"], "Dr")

    def test_phone_hidden_while_pending_revealed_after_accept(self):
        call_id = self._create().json()["id"]
        # Hali qabul qilinmagan — hech kimning telefoni ko'rinmasligi kerak.
        self.client.force_authenticate(self.vet_user)
        pending = self.client.get(reverse("v1:call-list"), {"role": "vet"}).json()["results"][0]
        self.assertNotIn("phone", pending["client_info"])
        self.client.force_authenticate(self.client_user)
        pending_c = self.client.get(reverse("v1:call-list"), {"role": "client"}).json()["results"][0]
        self.assertNotIn("phone", pending_c["vet_info"])

        # Qabul qilingach — ikkala tomon ham ko'radi.
        self.client.force_authenticate(self.vet_user)
        accepted = self.client.post(reverse("v1:call-action", args=[call_id, "accept"])).json()
        self.assertEqual(accepted["client_info"]["phone"], "+998901112233")
        self.client.force_authenticate(self.client_user)
        mine = self.client.get(reverse("v1:call-list"), {"role": "client"}).json()["results"][0]
        self.assertEqual(mine["vet_info"]["phone"], "+998904445566")

    def test_vet_cannot_create_call(self):
        self.client.force_authenticate(self.vet_user)
        resp = self.client.post(
            reverse("v1:call-list"),
            {"vet": self.vet.id, "type": "online"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_role_filtered_lists(self):
        self._create()
        # mijoz ko'radi
        self.client.force_authenticate(self.client_user)
        mine = self.client.get(reverse("v1:call-list"), {"role": "client"})
        self.assertEqual(mine.json()["count"], 1)
        # vet ko'radi
        self.client.force_authenticate(self.vet_user)
        incoming = self.client.get(reverse("v1:call-list"), {"role": "vet"})
        self.assertEqual(incoming.json()["count"], 1)

    def test_vet_accepts_then_completes(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        a = self.client.post(reverse("v1:call-action", args=[call_id, "accept"]))
        self.assertEqual(a.json()["status"], CallStatus.ACCEPTED)
        self.assertIsNotNone(a.json()["responded_at"])
        self.assertIsNone(a.json()["completed_at"])
        w = self.client.post(reverse("v1:call-action", args=[call_id, "on_way"]))
        self.assertEqual(w.json()["status"], CallStatus.ON_WAY)
        # on_way responded_at'ni o'zgartirmaydi (PENDING'dan birinchi chiqishda qo'yilgan edi).
        self.assertEqual(w.json()["responded_at"], a.json()["responded_at"])
        c = self.client.post(reverse("v1:call-action", args=[call_id, "complete"]))
        self.assertEqual(c.json()["status"], CallStatus.COMPLETED)
        self.assertIsNotNone(c.json()["completed_at"])

    def test_reject_sets_responded_at(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        r = self.client.post(reverse("v1:call-action", args=[call_id, "reject"]))
        self.assertEqual(r.json()["status"], CallStatus.REJECTED)
        self.assertIsNotNone(r.json()["responded_at"])

    def test_invalid_transition_rejected(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        # pending -> complete to'g'ridan mumkin emas
        resp = self.client.post(reverse("v1:call-action", args=[call_id, "complete"]))
        self.assertEqual(resp.status_code, 400)

    def test_vet_sets_price_after_accepting(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        self.client.post(reverse("v1:call-action", args=[call_id, "accept"]))
        resp = self.client.post(
            reverse("v1:call-set-price", args=[call_id]), {"price_agreed": "150000"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["price_agreed"], "150000.00")

    def test_cannot_set_price_before_accepting(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        resp = self.client.post(
            reverse("v1:call-set-price", args=[call_id]), {"price_agreed": "100000"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_client_cannot_set_price(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        self.client.post(reverse("v1:call-action", args=[call_id, "accept"]))
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(
            reverse("v1:call-set-price", args=[call_id]), {"price_agreed": "100000"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_negative_price_rejected(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        self.client.post(reverse("v1:call-action", args=[call_id, "accept"]))
        resp = self.client.post(
            reverse("v1:call-set-price", args=[call_id]), {"price_agreed": "-500"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_other_vet_cannot_act(self):
        call_id = self._create().json()["id"]
        intruder = User.objects.create(username="x", telegram_id=9, role=Role.VET)
        VetProfile.objects.create(user=intruder)
        self.client.force_authenticate(intruder)
        resp = self.client.post(reverse("v1:call-action", args=[call_id, "accept"]))
        self.assertEqual(resp.status_code, 403)

    def test_client_cancels(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(reverse("v1:call-action", args=[call_id, "cancel"]))
        self.assertEqual(resp.json()["status"], CallStatus.CANCELLED)


# ============================ REJIM B (tender) ============================

class TenderTests(Base):
    def _create_sr(self):
        self.client.force_authenticate(self.client_user)
        return self.client.post(
            reverse("v1:sr-list"),
            {"specialization": self.spec.id, "type": "home", "city": "Toshkent", "note": "Kasal"},
            format="json",
        )

    def test_client_creates_tender(self):
        resp = self._create_sr()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["status"], ServiceStatus.OPEN)

    def test_vet_sees_matching_feed(self):
        self._create_sr()
        self.client.force_authenticate(self.vet_user)
        feed = self.client.get(reverse("v1:sr-feed"))
        self.assertEqual(feed.json()["count"], 1)

    def test_vet_feed_excludes_unmatched_spec(self):
        self._create_sr()
        other_spec = Specialization.objects.create(name="Test-Qush", slug="tq")
        self.vet.specializations.clear()
        self.vet.specializations.add(other_spec)
        self.client.force_authenticate(self.vet_user)
        feed = self.client.get(reverse("v1:sr-feed"))
        self.assertEqual(feed.json()["count"], 0)

    def test_vet_submits_offer_and_duplicate_rejected(self):
        sr_id = self._create_sr().json()["id"]
        self.client.force_authenticate(self.vet_user)
        url = reverse("v1:sr-offer-create", args=[sr_id])
        first = self.client.post(url, {"price": "120000", "message": "Boraman"}, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        dup = self.client.post(url, {"price": "100000"}, format="json")
        self.assertEqual(dup.status_code, 400)

    def test_client_accepts_offer_assigns_and_declines_rest(self):
        sr_id = self._create_sr().json()["id"]
        sr = ServiceRequest.objects.get(id=sr_id)
        # ikki vetdan taklif
        v2_user = User.objects.create(username="v2", telegram_id=7, role=Role.VET)
        v2 = VetProfile.objects.create(user=v2_user)
        o1 = Offer.objects.create(request=sr, vet=self.vet, price=120000)
        o2 = Offer.objects.create(request=sr, vet=v2, price=90000)

        self.client.force_authenticate(self.client_user)
        # takliflarni ko'rish
        offers = self.client.get(reverse("v1:sr-offers", args=[sr_id]))
        self.assertEqual(len(offers.json()), 2)
        # o1 ni qabul qilish
        resp = self.client.post(reverse("v1:offer-accept", args=[o1.id]))
        self.assertEqual(resp.status_code, 200, resp.content)

        sr.refresh_from_db(); o1.refresh_from_db(); o2.refresh_from_db()
        self.assertEqual(sr.status, ServiceStatus.ASSIGNED)
        self.assertEqual(sr.assigned_offer_id, o1.id)
        self.assertEqual(o1.status, OfferStatus.ACCEPTED)
        self.assertEqual(o2.status, OfferStatus.DECLINED)

    def test_offer_browsing_has_no_phone_but_assigned_does(self):
        sr_id = self._create_sr().json()["id"]
        sr = ServiceRequest.objects.get(id=sr_id)
        offer = Offer.objects.create(request=sr, vet=self.vet, price=120000)

        self.client.force_authenticate(self.client_user)
        # Hali tanlanmagan — takliflar ro'yxatida vet telefoni ko'rinmaydi.
        offers = self.client.get(reverse("v1:sr-offers", args=[sr_id])).json()
        self.assertNotIn("phone", offers[0]["vet_info"])

        # Taklif qabul qilingach — vet telefoni assigned_offer_info'da chiqadi.
        self.client.post(reverse("v1:offer-accept", args=[offer.id]))
        sr_data = self.client.get(reverse("v1:sr-list")).json()["results"][0]
        self.assertEqual(sr_data["assigned_offer_info"]["vet_info"]["phone"], "+998904445566")

        # G'olib vet ham mijoz telefonini ko'radi.
        self.client.force_authenticate(self.vet_user)
        won = self.client.get(reverse("v1:sr-won")).json()
        self.assertEqual(won[0]["client_info"]["phone"], "+998901112233")

    def test_client_info_hidden_until_assigned_then_only_to_winner(self):
        sr_id = self._create_sr().json()["id"]
        sr = ServiceRequest.objects.get(id=sr_id)
        v2_user = User.objects.create(username="v2", telegram_id=7, role=Role.VET)
        v2 = VetProfile.objects.create(user=v2_user)
        o1 = Offer.objects.create(request=sr, vet=self.vet, price=120000)

        # Ochiq holatda — hech kimga mijoz ma'lumoti ko'rinmaydi.
        self.client.force_authenticate(self.vet_user)
        feed = self.client.get(reverse("v1:sr-feed")).json()["results"]
        self.assertIsNone(next(r for r in feed if r["id"] == sr_id)["client_info"])

        self.client.force_authenticate(self.client_user)
        self.client.post(reverse("v1:offer-accept", args=[o1.id]))

        # G'olib vetga ko'rinadi.
        self.client.force_authenticate(self.vet_user)
        won = self.client.get(reverse("v1:sr-won")).json()
        self.assertEqual(won[0]["client_info"]["id"], self.client_user.id)

        # Boshqa vetga ko'rinmaydi.
        self.client.force_authenticate(v2_user)
        feed2 = self.client.get(reverse("v1:sr-feed")).json()["results"]
        self.assertEqual(feed2, [])  # tayinlangani uchun lentada umuman yo'q

    def test_vet_completes_assigned_tender_sets_completed_at(self):
        sr_id = self._create_sr().json()["id"]
        sr = ServiceRequest.objects.get(id=sr_id)
        offer = Offer.objects.create(request=sr, vet=self.vet, price=120000, status=OfferStatus.ACCEPTED)
        sr.status = ServiceStatus.ASSIGNED
        sr.assigned_offer = offer
        sr.save()

        self.client.force_authenticate(self.vet_user)
        resp = self.client.post(reverse("v1:sr-complete", args=[sr_id]))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], ServiceStatus.COMPLETED)
        self.assertIsNotNone(resp.json()["completed_at"])

    def test_offer_on_assigned_request_rejected(self):
        sr_id = self._create_sr().json()["id"]
        sr = ServiceRequest.objects.get(id=sr_id)
        sr.status = ServiceStatus.ASSIGNED
        sr.save()
        self.client.force_authenticate(self.vet_user)
        resp = self.client.post(
            reverse("v1:sr-offer-create", args=[sr_id]), {"price": "100"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_vet_withdraws_offer(self):
        sr_id = self._create_sr().json()["id"]
        sr = ServiceRequest.objects.get(id=sr_id)
        offer = Offer.objects.create(request=sr, vet=self.vet, price=120000)
        self.client.force_authenticate(self.vet_user)
        resp = self.client.post(reverse("v1:offer-withdraw", args=[offer.id]))
        self.assertEqual(resp.status_code, 200)
        offer.refresh_from_db()
        self.assertEqual(offer.status, OfferStatus.WITHDRAWN)

    def test_client_cancels_tender(self):
        sr_id = self._create_sr().json()["id"]
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(reverse("v1:sr-cancel", args=[sr_id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            ServiceRequest.objects.get(id=sr_id).status, ServiceStatus.CANCELLED
        )


# ==================== So'rov yaratishga spam cheklovi ====================

class CreateThrottleTests(Base):
    def setUp(self):
        super().setUp()
        # Throttle keshi testlar orasida sizib o'tmasin.
        from django.core.cache import cache
        cache.clear()

    def test_call_creation_throttled_after_limit_listing_unaffected(self):
        self.client.force_authenticate(self.client_user)
        for _ in range(20):
            resp = self.client.post(
                reverse("v1:call-list"),
                {"vet": self.vet.id, "type": "online"}, format="json",
            )
            self.assertEqual(resp.status_code, 201, resp.content)
        blocked = self.client.post(
            reverse("v1:call-list"), {"vet": self.vet.id, "type": "online"}, format="json",
        )
        self.assertEqual(blocked.status_code, 429)
        # Limitga tegib turgan bo'lsa ham, ro'yxatni ko'rish (GET) bloklanmaydi.
        listing = self.client.get(reverse("v1:call-list"))
        self.assertEqual(listing.status_code, 200)

    def test_tender_creation_throttled_after_limit(self):
        self.client.force_authenticate(self.client_user)
        for _ in range(10):
            resp = self.client.post(
                reverse("v1:sr-list"),
                {"specialization": self.spec.id, "type": "home", "city": "Toshkent"}, format="json",
            )
            self.assertEqual(resp.status_code, 201, resp.content)
        blocked = self.client.post(
            reverse("v1:sr-list"),
            {"specialization": self.spec.id, "type": "home", "city": "Toshkent"}, format="json",
        )
        self.assertEqual(blocked.status_code, 429)


# ==================== Davriy vazifa: javobsiz chaqiruvni yopish ====================

@override_settings(CALL_RESPONSE_TIMEOUT_MINUTES=30)
class ExpireUnansweredCallsTests(Base):
    def _stale_call(self, **extra):
        call = CallRequest.objects.create(
            client=self.client_user, vet=self.vet, type="home", **extra
        )
        CallRequest.objects.filter(pk=call.pk).update(
            created_at=timezone.now() - timedelta(minutes=45)
        )
        call.refresh_from_db()
        return call

    def test_stale_pending_call_expires_and_notifies_client(self):
        call = self._stale_call()
        n = expire_unanswered_calls()
        call.refresh_from_db()
        self.assertEqual(n, 1)
        self.assertEqual(call.status, CallStatus.EXPIRED)
        # javob tezligi statistikasi buzilmasin — bu "javob" emas.
        self.assertIsNone(call.responded_at)
        self.assertTrue(
            Notification.objects.filter(recipient=self.client_user, call_request=call).exists()
        )

    def test_fresh_pending_call_not_touched(self):
        call = CallRequest.objects.create(client=self.client_user, vet=self.vet, type="home")
        expire_unanswered_calls()
        call.refresh_from_db()
        self.assertEqual(call.status, CallStatus.PENDING)

    def test_already_accepted_call_not_touched(self):
        call = self._stale_call(status=CallStatus.ACCEPTED)
        expire_unanswered_calls()
        call.refresh_from_db()
        self.assertEqual(call.status, CallStatus.ACCEPTED)


class ClientLocationPrivacyTests(Base):
    """Mijozning aniq joyi vetga faqat bog'langach ko'rinadi, undan oldin — masofa."""

    def setUp(self):
        super().setUp()
        self.vet.lat, self.vet.lng = 41.30, 69.24
        self.vet.save()

    def test_call_location_hidden_until_accepted(self):
        self.client.force_authenticate(self.client_user)
        call_id = self.client.post(
            reverse("v1:call-list"),
            {"vet": self.vet.id, "type": "home", "address": "Uy 5", "lat": 41.31, "lng": 69.25},
            format="json",
        ).json()["id"]

        mine = self.client.get(reverse("v1:call-list"), {"role": "client"}).json()["results"][0]
        self.assertEqual((mine["lat"], mine["address"]), (41.31, "Uy 5"))

        self.client.force_authenticate(self.vet_user)
        pending = self.client.get(reverse("v1:call-list"), {"role": "vet"}).json()["results"][0]
        self.assertIsNone(pending["lat"])
        self.assertEqual(pending["address"], "")
        self.assertTrue(pending["location_hidden"])
        self.assertIsNotNone(pending["distance_km"])

        accepted = self.client.post(reverse("v1:call-action", args=[call_id, "accept"])).json()
        self.assertEqual((accepted["lat"], accepted["lng"], accepted["address"]), (41.31, 69.25, "Uy 5"))
        self.assertFalse(accepted["location_hidden"])

    def test_tender_location_only_for_winner(self):
        other_user = User.objects.create(username="vet2", telegram_id=3, role=Role.VET)
        other = VetProfile.objects.create(user=other_user, city="Toshkent", lat=41.0, lng=69.0)
        other.specializations.add(self.spec)

        self.client.force_authenticate(self.client_user)
        sr_id = self.client.post(
            reverse("v1:sr-list"),
            {"specialization": self.spec.id, "type": "home", "city": "Toshkent", "lat": 41.31, "lng": 69.25},
            format="json",
        ).json()["id"]

        self.client.force_authenticate(self.vet_user)
        feed = self.client.get(reverse("v1:sr-feed")).json()
        item = next(i for i in feed.get("results", feed) if i["id"] == sr_id)
        self.assertIsNone(item["lat"])
        self.assertTrue(item["location_hidden"])
        self.assertIsNotNone(item["distance_km"])

        offer_id = self.client.post(reverse("v1:sr-offer-create", args=[sr_id]), {"price": 100000}, format="json").json()["id"]
        self.client.force_authenticate(self.client_user)
        self.client.post(reverse("v1:offer-accept", args=[offer_id]))

        self.client.force_authenticate(self.vet_user)
        won = self.client.get(reverse("v1:sr-won")).json()
        won_item = next(i for i in won if i["id"] == sr_id)
        self.assertEqual((won_item["lat"], won_item["lng"]), (41.31, 69.25))

        # Yutqazgan vet aniq joyni ko'rmaydi
        self.client.force_authenticate(other_user)
        resp = self.client.get(reverse("v1:sr-feed")).json()
        self.assertFalse(any(i["id"] == sr_id and i["lat"] is not None for i in resp.get("results", resp)))


class RegionMatchingTests(Base):
    def test_region_q_matches_full_and_legacy_names(self):
        from apps.vets.utils import region_q

        self.vet.city = "Samarqand"
        self.vet.save()
        full_user = User.objects.create(username="v3", telegram_id=4, role=Role.VET)
        full = VetProfile.objects.create(user=full_user, city="Samarqand viloyati")
        other_user = User.objects.create(username="v4", telegram_id=5, role=Role.VET)
        VetProfile.objects.create(user=other_user, city="Buxoro viloyati")

        ids = set(VetProfile.objects.filter(region_q("city", "Samarqand viloyati")).values_list("id", flat=True))
        self.assertEqual(ids, {self.vet.id, full.id})
