from rest_framework import status
from rest_framework.test import APITestCase

from .models import Testimonial


class TestimonialSmokeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        Testimonial.objects.create(name="Rajiv Kapoor", role="Business Owner", content="Great")
        Testimonial.objects.create(name="Inactive", content="x", is_active=False)

    def test_list_returns_active_only(self):
        r = self.client.get("/api/v1/testimonials/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
