"""Step 6: tests for the recently-viewed by-ids endpoint."""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, City

from .models import Project


class ProjectByIdsTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(name="Noida")
        cls.cat = Category.objects.create(name="Residential")
        cls.projects = [
            Project.objects.create(
                title=f"Project {i}",
                category=cls.cat, city=cls.city,
                is_published=True,
            )
            for i in range(25)
        ]
        cls.draft = Project.objects.create(
            title="Draft", category=cls.cat, city=cls.city, is_published=False,
        )

    def setUp(self):
        cache.clear()

    def test_empty_ids_param_returns_empty_list(self):
        r = self.client.get("/api/v1/projects/by-ids/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data, [])

    def test_preserves_input_order(self):
        # Pick three out-of-order ids and assert the response order matches.
        a, b, c = self.projects[2], self.projects[10], self.projects[0]
        ids = f"{a.pk},{b.pk},{c.pk}"
        r = self.client.get("/api/v1/projects/by-ids/", {"ids": ids})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [row["id"] for row in r.data],
            [a.pk, b.pk, c.pk],
        )

    def test_unknown_ids_are_silently_dropped(self):
        a = self.projects[0]
        r = self.client.get(
            "/api/v1/projects/by-ids/", {"ids": f"{a.pk},999999,abc,{a.pk}"},
        )
        # 999999 → unknown (drop), `abc` → non-int (drop), duplicate `a.pk` → dedupe.
        self.assertEqual([row["id"] for row in r.data], [a.pk])

    def test_unpublished_excluded(self):
        a = self.projects[0]
        r = self.client.get(
            "/api/v1/projects/by-ids/", {"ids": f"{a.pk},{self.draft.pk}"},
        )
        self.assertEqual([row["id"] for row in r.data], [a.pk])

    def test_clamps_at_20_ids(self):
        ids = ",".join(str(p.pk) for p in self.projects)  # 25 ids
        r = self.client.get("/api/v1/projects/by-ids/", {"ids": ids})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 20)
        # First 20 in input order = first 20 ordered_ids.
        self.assertEqual(
            [row["id"] for row in r.data],
            [self.projects[i].pk for i in range(20)],
        )

    def test_response_is_lightweight_list_shape(self):
        a = self.projects[0]
        r = self.client.get("/api/v1/projects/by-ids/", {"ids": str(a.pk)})
        row = r.data[0]
        # Same shape as the list endpoint — no `description`, no nested children.
        self.assertIn("image_count", row)
        self.assertIn("cover_thumbnail", row)
        self.assertNotIn("description", row)
        self.assertNotIn("floor_plans", row)
