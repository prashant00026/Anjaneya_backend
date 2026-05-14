from rest_framework import status
from rest_framework.test import APITestCase

from .models import TeamMember


class TeamSmokeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        TeamMember.objects.create(
            name="Rohit Aggarwal", designation="Founder & CEO",
        )
        TeamMember.objects.create(
            name="Inactive Member", designation="Test", is_active=False,
        )

    def test_list_returns_active_only(self):
        r = self.client.get("/api/v1/team/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["name"], "Rohit Aggarwal")

    def test_detail_by_slug(self):
        r = self.client.get("/api/v1/team/rohit-aggarwal/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
