"""vets API testlari (ARCHITECTURE.md 6.3)."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User

from .models import Service, Specialization, VetProfile


class VetProfileTests(APITestCase):
    def setUp(self):
        self.vet = User.objects.create(
            username="vet1", telegram_id=111, role=Role.VET, first_name="Aziz"
        )
        self.client_user = User.objects.create(
            username="cli1", telegram_id=222, role=Role.CLIENT
        )
        self.spec = Specialization.objects.create(name="Mushuklar", slug="mushuklar", icon="🐱")

    def test_vet_get_me_autocreates_profile(self):
        self.client.force_authenticate(self.vet)
        resp = self.client.get(reverse("v1:vet-me"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(VetProfile.objects.filter(user=self.vet).exists())

    def test_vet_update_profile(self):
        self.client.force_authenticate(self.vet)
        resp = self.client.patch(
            reverse("v1:vet-me"),
            {
                "bio": "10 yillik tajriba",
                "city": "Toshkent",
                "experience_years": 10,
                "specialization_ids": [self.spec.id],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        profile = VetProfile.objects.get(user=self.vet)
        self.assertEqual(profile.city, "Toshkent")
        self.assertEqual(profile.experience_years, 10)
        self.assertIn(self.spec, profile.specializations.all())

    def test_vet_uploads_license_document(self):
        self.client.force_authenticate(self.vet)
        pdf = SimpleUploadedFile("diplom.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        resp = self.client.patch(
            reverse("v1:vet-me"), {"license_document": pdf}, format="multipart"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["license_document"])
        profile = VetProfile.objects.get(user=self.vet)
        self.assertTrue(profile.license_document.name)

    def test_license_document_rejects_bad_extension(self):
        self.client.force_authenticate(self.vet)
        bad = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        resp = self.client.patch(
            reverse("v1:vet-me"), {"license_document": bad}, format="multipart"
        )
        self.assertEqual(resp.status_code, 400)

    def test_vet_cannot_set_verified(self):
        self.client.force_authenticate(self.vet)
        resp = self.client.patch(
            reverse("v1:vet-me"), {"is_verified": True}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(VetProfile.objects.get(user=self.vet).is_verified)

    def test_client_forbidden_on_vet_me(self):
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:vet-me"))
        self.assertEqual(resp.status_code, 403)

    def test_availability_toggle(self):
        self.client.force_authenticate(self.vet)
        resp = self.client.put(
            reverse("v1:vet-availability"), {"is_available": False}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_available"])

    def test_service_crud(self):
        self.client.force_authenticate(self.vet)
        # create
        create = self.client.post(
            reverse("v1:vet-services"),
            {"title": "Emlash", "price": "150000", "duration_min": 30},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.content)
        sid = create.json()["id"]
        # list
        lst = self.client.get(reverse("v1:vet-services"))
        self.assertEqual(len(lst.json()), 1)
        # delete
        dele = self.client.delete(
            reverse("v1:vet-service-detail", args=[sid])
        )
        self.assertEqual(dele.status_code, 204)
        self.assertFalse(Service.objects.filter(id=sid).exists())

    def test_specializations_list(self):
        self.client.force_authenticate(self.vet)
        resp = self.client.get(reverse("v1:specialization-list"))
        self.assertEqual(resp.status_code, 200)
        # Seed-migratsiya + setUp'dagi bittasi
        self.assertEqual(len(resp.json()), Specialization.objects.count())
        names = [s["name"] for s in resp.json()]
        self.assertIn("Mushuklar", names)


class VetSearchTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create(
            username="cli", telegram_id=900, role=Role.CLIENT
        )
        self.cats = Specialization.objects.create(name="Test-Mushuk", slug="m", icon="🐱")
        self.dogs = Specialization.objects.create(name="Test-It", slug="i", icon="🐕")

        # Toshkent markazi (~41.31, 69.28). Yaqin va uzoq vet.
        self.near = self._make_vet("near", 901, lat=41.32, lng=69.27, rating=4.0)
        self.far = self._make_vet("far", 902, lat=41.80, lng=69.90, rating=5.0)
        self.near.specializations.add(self.cats)
        self.far.specializations.add(self.dogs)

    def _make_vet(self, uname, tg, lat, lng, rating, is_top=False, online=True):
        u = User.objects.create(
            username=uname, telegram_id=tg, role=Role.VET, first_name=uname
        )
        return VetProfile.objects.create(
            user=u, lat=lat, lng=lng, city="Toshkent",
            rating_avg=rating, accepts_online=online, is_top=is_top,
        )

    def test_search_requires_auth(self):
        resp = self.client.get(reverse("v1:vet-search"))
        self.assertEqual(resp.status_code, 401)

    def test_list_returns_all(self):
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:vet-search"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 2)

    def test_filter_by_specialization(self):
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:vet-search"), {"spec": "m"})
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.near.id)

    def test_filter_by_type_online(self):
        self.far.accepts_online = False
        self.far.save()
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:vet-search"), {"type": "online"})
        ids = [r["id"] for r in resp.json()["results"]]
        self.assertIn(self.near.id, ids)
        self.assertNotIn(self.far.id, ids)

    def test_sort_by_distance(self):
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(
            reverse("v1:vet-search"),
            {"sort": "distance", "lat": "41.31", "lng": "69.28"},
        )
        results = resp.json()["results"]
        self.assertEqual(results[0]["id"], self.near.id)  # yaqinroq oldinda
        self.assertIsNotNone(results[0]["distance_km"])
        self.assertLess(results[0]["distance_km"], results[1]["distance_km"])

    def test_top_vet_first(self):
        self.far.is_top = True
        self.far.save()
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:vet-search"))
        self.assertEqual(resp.json()["results"][0]["id"], self.far.id)

    def test_vet_detail(self):
        Service.objects.create(vet=self.near, title="Emlash", price=100000)
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:vet-detail", args=[self.near.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["services"]), 1)
        self.assertEqual(float(resp.json()["min_price"]), 100000.0)
