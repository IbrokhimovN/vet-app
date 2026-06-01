"""requests testlari — REJIM A (chaqiruv) va REJIM B (tender)."""
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.pets.models import Pet
from apps.vets.models import Specialization, VetProfile

from .models import CallRequest, CallStatus, Offer, OfferStatus, ServiceRequest, ServiceStatus


class Base(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create(username="cli", telegram_id=1, role=Role.CLIENT)
        self.vet_user = User.objects.create(username="vet", telegram_id=2, role=Role.VET, first_name="Dr")
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
        w = self.client.post(reverse("v1:call-action", args=[call_id, "on_way"]))
        self.assertEqual(w.json()["status"], CallStatus.ON_WAY)
        c = self.client.post(reverse("v1:call-action", args=[call_id, "complete"]))
        self.assertEqual(c.json()["status"], CallStatus.COMPLETED)

    def test_invalid_transition_rejected(self):
        call_id = self._create().json()["id"]
        self.client.force_authenticate(self.vet_user)
        # pending -> complete to'g'ridan mumkin emas
        resp = self.client.post(reverse("v1:call-action", args=[call_id, "complete"]))
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
