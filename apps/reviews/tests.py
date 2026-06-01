"""Izoh / reyting testlari (7-bosqich)."""
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationKind
from apps.requests.models import CallRequest, CallStatus
from apps.vets.models import VetProfile

from .models import Review


class Base(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create(username="cli", telegram_id=1, role=Role.CLIENT)
        self.vet_user = User.objects.create(username="vet", telegram_id=2, role=Role.VET, first_name="Dr")
        self.vet = VetProfile.objects.create(user=self.vet_user)

    def _call(self, status=CallStatus.COMPLETED):
        return CallRequest.objects.create(
            client=self.client_user, vet=self.vet, type="online", status=status
        )


class ReviewCreateTests(Base):
    def test_client_reviews_completed_call(self):
        call = self._call()
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(
            reverse("v1:review-create"),
            {"request": call.id, "stars": 5, "comment": "Zo'r"}, format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["stars"], 5)
        self.assertEqual(resp.json()["client_name"], "Mijoz")

    def test_rating_recomputed(self):
        c1, c2 = self._call(), self._call()
        Review.objects.create(client=self.client_user, vet=self.vet, request=c1, stars=4)
        Review.objects.create(client=self.client_user, vet=self.vet, request=c2, stars=5)
        self.vet.refresh_from_db()
        self.assertEqual(self.vet.rating_count, 2)
        self.assertEqual(self.vet.rating_avg, Decimal("4.50"))

    def test_rating_recomputed_on_delete(self):
        c1, c2 = self._call(), self._call()
        r1 = Review.objects.create(client=self.client_user, vet=self.vet, request=c1, stars=4)
        Review.objects.create(client=self.client_user, vet=self.vet, request=c2, stars=2)
        r1.delete()
        self.vet.refresh_from_db()
        self.assertEqual(self.vet.rating_count, 1)
        self.assertEqual(self.vet.rating_avg, Decimal("2.00"))

    def test_cannot_review_unfinished_call(self):
        call = self._call(status=CallStatus.ACCEPTED)
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(
            reverse("v1:review-create"),
            {"request": call.id, "stars": 5}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cannot_review_twice(self):
        call = self._call()
        Review.objects.create(client=self.client_user, vet=self.vet, request=call, stars=3)
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(
            reverse("v1:review-create"),
            {"request": call.id, "stars": 4}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cannot_review_others_call(self):
        call = self._call()
        other = User.objects.create(username="x", telegram_id=9, role=Role.CLIENT)
        self.client.force_authenticate(other)
        resp = self.client.post(
            reverse("v1:review-create"),
            {"request": call.id, "stars": 4}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_stars_out_of_range_rejected(self):
        call = self._call()
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(
            reverse("v1:review-create"),
            {"request": call.id, "stars": 6}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_review_notifies_vet(self):
        call = self._call()
        self.client.force_authenticate(self.client_user)
        self.client.post(
            reverse("v1:review-create"),
            {"request": call.id, "stars": 5, "comment": "Rahmat"}, format="json",
        )
        n = Notification.objects.get(recipient=self.vet_user)
        self.assertEqual(n.kind, NotificationKind.REVIEW_NEW)
        self.assertEqual(n.bot, "vet")


class VetReviewListTests(Base):
    def test_list_vet_reviews(self):
        c1, c2 = self._call(), self._call()
        Review.objects.create(client=self.client_user, vet=self.vet, request=c1, stars=5, comment="A")
        Review.objects.create(client=self.client_user, vet=self.vet, request=c2, stars=4, comment="B")
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:vet-reviews", args=[self.vet.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)
