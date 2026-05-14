from rest_framework import status
from rest_framework.test import APITestCase

from .models import Amenity, Category, City, Developer


class CatalogSmokeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        City.objects.create(name="Noida")
        Category.objects.create(name="Residential")
        Developer.objects.create(name="CRC Group")
        Amenity.objects.create(name="Ample Parking")

    def test_cities_list(self):
        r = self.client.get("/api/v1/cities/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["count"], 1)

    def test_city_detail_by_slug(self):
        r = self.client.get("/api/v1/cities/noida/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["slug"], "noida")

    def test_categories_list(self):
        r = self.client.get("/api/v1/categories/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_developers_list(self):
        r = self.client.get("/api/v1/developers/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_amenities_list(self):
        r = self.client.get("/api/v1/amenities/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
