from rest_framework import status
from rest_framework.test import APITestCase

from .models import Enquiry


class EnquirySmokeTests(APITestCase):
    URL = "/api/v1/enquiries/"

    def test_public_post_creates_enquiry(self):
        r = self.client.post(self.URL, {
            "full_name": "Test User",
            "mobile": "+919999999999",
            "email": "t@example.com",
            "message": "I'm interested",
            "source": "contact_page",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(Enquiry.objects.count(), 1)
        obj = Enquiry.objects.get()
        self.assertEqual(obj.full_name, "Test User")
        self.assertEqual(obj.status, Enquiry.Status.NEW)

    def test_honeypot_rejects_spam(self):
        r = self.client.post(self.URL, {
            "full_name": "Spam Bot",
            "mobile": "0",
            "website": "http://spam.example/",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_get_is_method_not_allowed(self):
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
