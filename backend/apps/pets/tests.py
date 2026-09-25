"""pets API testlari."""
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User

from .models import Pet


class PetTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create(username="c", telegram_id=1, role=Role.CLIENT)
        self.other = User.objects.create(username="o", telegram_id=2, role=Role.CLIENT)

    def test_create_and_list_own_pet(self):
        self.client.force_authenticate(self.client_user)
        create = self.client.post(
            reverse("v1:pet-list"),
            {"name": "Rex", "species": "It", "age": 3},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.content)
        lst = self.client.get(reverse("v1:pet-list"))
        self.assertEqual(len(lst.json()), 1)
        self.assertEqual(lst.json()[0]["name"], "Rex")

    def test_cannot_access_others_pet(self):
        pet = Pet.objects.create(owner=self.other, name="Mosi", species="Mushuk")
        self.client.force_authenticate(self.client_user)
        resp = self.client.get(reverse("v1:pet-detail", args=[pet.id]))
        self.assertEqual(resp.status_code, 404)
