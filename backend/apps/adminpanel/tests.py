"""Admin panel API testlari: ruxsat chegarasi va asosiy amallar."""
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.moderation.models import Report, ReportReason
from apps.notifications.models import Notification, NotificationKind
from apps.requests.models import CallRequest, CallStatus, Offer, ServiceRequest, ServiceStatus
from apps.reviews.models import Review
from apps.vets.models import VetProfile


class AdminBase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="boss", password="s3cret-pass-1", is_staff=True, is_superuser=True
        )
        self.client_user = User.objects.create(username="cli", telegram_id=1, role=Role.CLIENT)
        self.vet_user = User.objects.create(username="vet", telegram_id=2, role=Role.VET, first_name="Dr")
        self.vet = VetProfile.objects.create(user=self.vet_user)


class PermissionTests(AdminBase):
    def test_anonymous_rejected(self):
        self.assertEqual(self.client.get(reverse("v1:admin-stats")).status_code, 401)

    def test_non_staff_forbidden_everywhere(self):
        self.client.force_authenticate(self.client_user)
        for name in ("admin-stats", "admin-users", "admin-vets", "admin-calls",
                     "admin-tenders", "admin-reviews", "admin-reports"):
            self.assertEqual(self.client.get(reverse(f"v1:{name}")).status_code, 403, name)
        self.assertEqual(
            self.client.post(reverse("v1:admin-vet-toggle", args=[self.vet.id])).status_code, 403
        )


class LoginTests(AdminBase):
    def test_staff_can_login(self):
        resp = self.client.post(
            reverse("v1:admin-login"), {"username": "boss", "password": "s3cret-pass-1"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("access", resp.json())
        self.assertTrue(resp.json()["user"]["is_superuser"])

    def test_non_staff_cannot_login(self):
        User.objects.create_user(username="plain", password="s3cret-pass-1")
        resp = self.client.post(
            reverse("v1:admin-login"), {"username": "plain", "password": "s3cret-pass-1"}, format="json"
        )
        self.assertEqual(resp.status_code, 401)

    def test_wrong_password(self):
        resp = self.client.post(
            reverse("v1:admin-login"), {"username": "boss", "password": "nope"}, format="json"
        )
        self.assertEqual(resp.status_code, 401)


class ActionTests(AdminBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.admin)

    def test_stats(self):
        resp = self.client.get(reverse("v1:admin-stats"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total_vets"], 1)
        self.assertEqual(resp.json()["unverified_vets"], 1)

    def test_stats_kpis_null_without_data(self):
        resp = self.client.get(reverse("v1:admin-stats"))
        data = resp.json()
        self.assertIsNone(data["avg_response_minutes"])
        self.assertIsNone(data["completion_rate"])
        self.assertIsNone(data["avg_offers_per_tender"])

    def test_stats_kpis_computed(self):
        now = timezone.now()
        call = CallRequest.objects.create(
            client=self.client_user, vet=self.vet, type="home", status=CallStatus.COMPLETED
        )
        CallRequest.objects.filter(pk=call.pk).update(
            responded_at=now, completed_at=now
        )
        sr = ServiceRequest.objects.create(client=self.client_user, type="home", status=ServiceStatus.OPEN)
        Offer.objects.create(request=sr, vet=self.vet, price=100000)

        data = self.client.get(reverse("v1:admin-stats")).json()
        self.assertEqual(data["avg_response_minutes"], 0.0)
        self.assertEqual(data["completion_rate"], 100.0)
        self.assertEqual(data["avg_offers_per_tender"], 1.0)

    def test_toggle_verify(self):
        url = reverse("v1:admin-vet-toggle", args=[self.vet.id])
        self.client.post(url)
        self.vet.refresh_from_db()
        self.assertTrue(self.vet.is_verified)
        self.client.post(url)
        self.vet.refresh_from_db()
        self.assertFalse(self.vet.is_verified)

    def test_vet_list_falls_back_to_username(self):
        nameless = User.objects.create(username="nameless", telegram_id=3, role=Role.VET)
        VetProfile.objects.create(user=nameless)
        names = {v["full_name"] for v in self.client.get(reverse("v1:admin-vets")).json()["results"]}
        self.assertIn("nameless", names)

    def test_block_user_and_superuser_protected(self):
        resp = self.client.post(reverse("v1:admin-user-toggle", args=[self.client_user.id]))
        self.assertEqual(resp.status_code, 200)
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.is_active)
        resp = self.client.post(reverse("v1:admin-user-toggle", args=[self.admin.id]))
        self.assertEqual(resp.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_delete_user(self):
        target_id = self.client_user.id
        resp = self.client.delete(reverse("v1:admin-user-delete", args=[target_id]))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(User.objects.filter(id=target_id).exists())

    def test_delete_user_cascades_vet_profile(self):
        vet_id = self.vet.id
        resp = self.client.delete(reverse("v1:admin-user-delete", args=[self.vet_user.id]))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(VetProfile.objects.filter(id=vet_id).exists())

    def test_cannot_delete_superuser(self):
        resp = self.client.delete(reverse("v1:admin-user-delete", args=[self.admin.id]))
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_resolve_report(self):
        rep = Report.objects.create(
            reporter=self.client_user, reported_user=self.vet_user, reason=ReportReason.RUDE
        )
        self.assertEqual(self.client.get(reverse("v1:admin-stats")).json()["unresolved_reports"], 1)
        resp = self.client.post(reverse("v1:admin-report-resolve", args=[rep.id]))
        self.assertEqual(resp.status_code, 200)
        rep.refresh_from_db()
        self.assertTrue(rep.is_resolved)
        self.assertEqual(self.client.get(reverse("v1:admin-stats")).json()["unresolved_reports"], 0)

    def test_delete_review_recomputes_rating(self):
        call = CallRequest.objects.create(
            client=self.client_user, vet=self.vet, type="online", status=CallStatus.COMPLETED
        )
        review = Review.objects.create(
            request=call, vet=self.vet, client=self.client_user, stars=5, comment="ok"
        )
        self.vet.refresh_from_db()
        self.assertEqual(self.vet.rating_count, 1)
        resp = self.client.delete(reverse("v1:admin-review-delete", args=[review.id]))
        self.assertEqual(resp.status_code, 204)
        self.vet.refresh_from_db()
        self.assertEqual(self.vet.rating_count, 0)

    def test_notification_list_and_failed_filter(self):
        Notification.objects.create(
            recipient=self.vet_user, kind=NotificationKind.CALL_NEW, bot="vet",
            title="Test", body="x", is_sent=True,
        )
        failed = Notification.objects.create(
            recipient=self.vet_user, kind=NotificationKind.CALL_NEW, bot="vet",
            title="Test", body="x", is_sent=False, error="Timeout",
        )
        resp = self.client.get(reverse("v1:admin-notifications"))
        self.assertEqual(resp.json()["count"], 2)
        resp = self.client.get(reverse("v1:admin-notifications"), {"failed": "1"})
        self.assertEqual(resp.json()["count"], 1)
        self.assertEqual(resp.json()["results"][0]["id"], failed.id)
        self.assertEqual(self.client.get(reverse("v1:admin-stats")).json()["failed_notifications"], 1)

    @patch("apps.notifications.telegram.requests.post")
    def test_notification_retry_requeues_delivery(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True, "result": {"message_id": 1}}
        n = Notification.objects.create(
            recipient=self.vet_user, kind=NotificationKind.CALL_NEW, bot="vet",
            title="Test", body="x", is_sent=False, error="Timeout",
        )
        resp = self.client.post(reverse("v1:admin-notification-retry", args=[n.id]))
        self.assertEqual(resp.status_code, 200)
        n.refresh_from_db()
        self.assertTrue(n.is_sent)
        self.assertEqual(n.error, "")

    def test_notification_retry_on_already_sent_rejected(self):
        n = Notification.objects.create(
            recipient=self.vet_user, kind=NotificationKind.CALL_NEW, bot="vet",
            title="Test", body="x", is_sent=True,
        )
        resp = self.client.post(reverse("v1:admin-notification-retry", args=[n.id]))
        self.assertEqual(resp.status_code, 400)

    def test_toggle_top_sets_and_clears_top_until(self):
        url = reverse("v1:admin-vet-toggle-top", args=[self.vet.id])
        resp = self.client.post(url, {"days": 5}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.vet.refresh_from_db()
        self.assertTrue(self.vet.is_top)
        self.assertIsNotNone(self.vet.top_until)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.vet.refresh_from_db()
        self.assertFalse(self.vet.is_top)
        self.assertIsNone(self.vet.top_until)

    def test_toggle_top_rejects_bad_days(self):
        url = reverse("v1:admin-vet-toggle-top", args=[self.vet.id])
        resp = self.client.post(url, {"days": -3}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_wallet_adjust_credits_and_debits(self):
        url = reverse("v1:admin-vet-wallet-adjust", args=[self.vet.id])
        resp = self.client.post(url, {"amount": "50000"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.vet.refresh_from_db()
        self.assertEqual(self.vet.wallet_balance, 50000)
        resp = self.client.post(url, {"amount": "-20000"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.vet.refresh_from_db()
        self.assertEqual(self.vet.wallet_balance, 30000)

    def test_wallet_adjust_rejects_negative_result(self):
        url = reverse("v1:admin-vet-wallet-adjust", args=[self.vet.id])
        resp = self.client.post(url, {"amount": "-10"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.vet.refresh_from_db()
        self.assertEqual(self.vet.wallet_balance, 0)
