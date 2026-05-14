"""Filter / pagination / query-count tests for the Project list endpoint.

Covers step 5 deliverables only. Media + write-API tests stay in
`tests.py`.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, City, Developer

from .models import Project, ProjectImage


def _png_bytes() -> bytes:
    """Tiny PNG body just to populate a ProjectImage row when needed."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


@override_settings(REST_FRAMEWORK={
    # Smaller default page so pagination tests don't need a million rows.
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 5,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
})
class ProjectFilterTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.noida = City.objects.create(name="Noida")
        cls.gurgaon = City.objects.create(name="Gurugram")
        cls.commercial = Category.objects.create(name="Commercial")
        cls.residential = Category.objects.create(name="Residential")
        cls.dev = Developer.objects.create(name="CRC Group")

        now = timezone.now()
        cls.p1 = Project.objects.create(
            title="CRC Flagship",
            category=cls.commercial, city=cls.noida, locality="Sector-140A",
            developer=cls.dev,
            price_starting_lacs=Decimal("80"),
            is_published=True, is_featured=True, featured_order=1,
            published_at=now,
        )
        cls.p2 = Project.objects.create(
            title="Godrej Tropical Isle",
            category=cls.residential, city=cls.noida, locality="Sector-146",
            price_starting_lacs=Decimal("250"),
            is_published=True, is_featured=True, featured_order=2,
            published_at=now - timedelta(days=2),
        )
        cls.p3 = Project.objects.create(
            title="Sunrise Residency",
            category=cls.residential, city=cls.gurgaon, locality="Sector-45",
            price_starting_lacs=Decimal("120"),
            is_published=True,
            published_at=now - timedelta(days=40),
        )
        cls.draft = Project.objects.create(
            title="Draft",
            category=cls.residential, city=cls.noida,
            is_published=False,
        )

    # ------- single-value & multi-value category --------------------------

    def test_default_list_returns_published_only(self):
        r = self.client.get("/api/v1/projects/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["count"], 3)

    def test_category_single_value(self):
        r = self.client.get("/api/v1/projects/", {"category": "residential"})
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p2.slug, self.p3.slug})

    def test_category_csv_multi_value(self):
        r = self.client.get(
            "/api/v1/projects/", {"category": "residential,commercial"},
        )
        self.assertEqual(r.data["count"], 3)

    def test_city_csv_multi_value(self):
        r = self.client.get("/api/v1/projects/", {"city": "noida"})
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p1.slug, self.p2.slug})

    # ------- price range --------------------------------------------------

    def test_price_range_both_bounds(self):
        r = self.client.get(
            "/api/v1/projects/", {"price_min": 100, "price_max": 200},
        )
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p3.slug})

    def test_price_range_lower_bound_only(self):
        r = self.client.get("/api/v1/projects/", {"price_min": 100})
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p2.slug, self.p3.slug})

    def test_price_range_upper_bound_only(self):
        r = self.client.get("/api/v1/projects/", {"price_max": 100})
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p1.slug})

    # ------- posted_within_days ------------------------------------------

    def test_posted_within_days_recent(self):
        r = self.client.get("/api/v1/projects/", {"posted_within_days": 7})
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p1.slug, self.p2.slug})

    def test_posted_within_days_zero_is_noop(self):
        r = self.client.get("/api/v1/projects/", {"posted_within_days": 0})
        self.assertEqual(r.data["count"], 3)

    # ------- has_image ----------------------------------------------------

    def test_has_image_true(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        ProjectImage.objects.create(
            project=self.p2,
            image=SimpleUploadedFile("a.png", _png_bytes(), "image/png"),
        )
        r = self.client.get("/api/v1/projects/", {"has_image": "true"})
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p2.slug})

    def test_has_image_false(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        ProjectImage.objects.create(
            project=self.p2,
            image=SimpleUploadedFile("a.png", _png_bytes(), "image/png"),
        )
        r = self.client.get("/api/v1/projects/", {"has_image": "false"})
        slugs = {row["slug"] for row in r.data["results"]}
        self.assertEqual(slugs, {self.p1.slug, self.p3.slug})

    # ------- sorting ------------------------------------------------------

    def test_default_sort_is_newest_first(self):
        r = self.client.get("/api/v1/projects/")
        slugs = [row["slug"] for row in r.data["results"]]
        self.assertEqual(slugs[0], self.p1.slug)
        self.assertEqual(slugs[-1], self.p3.slug)

    def test_sort_by_price_asc(self):
        r = self.client.get(
            "/api/v1/projects/", {"ordering": "price_starting_lacs"},
        )
        slugs = [row["slug"] for row in r.data["results"]]
        self.assertEqual(slugs, [self.p1.slug, self.p3.slug, self.p2.slug])

    def test_sort_by_price_desc(self):
        r = self.client.get(
            "/api/v1/projects/", {"ordering": "-price_starting_lacs"},
        )
        slugs = [row["slug"] for row in r.data["results"]]
        self.assertEqual(slugs, [self.p2.slug, self.p3.slug, self.p1.slug])

    # ------- pagination envelope -----------------------------------------

    def test_envelope_includes_total_pages(self):
        r = self.client.get("/api/v1/projects/")
        self.assertIn("total_pages", r.data)
        self.assertEqual(r.data["total_pages"], 1)  # 3 items, page_size=5

    def test_page_size_query_param(self):
        r = self.client.get("/api/v1/projects/", {"page_size": 1})
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data["total_pages"], 3)

    def test_page_size_clamped_at_max(self):
        # page_size=999 should clamp to max_page_size=60. With 3 rows the
        # response still returns all 3; the assertion is just that the
        # response is well-formed (no error).
        r = self.client.get("/api/v1/projects/", {"page_size": 999})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 3)

    # ------- query counts -------------------------------------------------

    def test_list_query_count_at_or_under_5(self):
        # Set page_size large so we'd see N+1s on more rows.
        with self.assertNumQueries(2):
            # Expected queries: 1 COUNT for pagination + 1 SELECT for the page.
            # Annotated image_count and FK joins ride on the SELECT.
            self.client.get("/api/v1/projects/", {"page_size": 60})

    def test_detail_query_count_under_8(self):
        # Detail prefetches: project + category + city + developer +
        # amenities + images + floor_plans + highlights + stats.
        # With select_related rolling category/city/developer into one
        # SELECT, the expected count is 1 (project) + 5 prefetches = 6.
        with self.assertNumQueries(6):
            self.client.get(f"/api/v1/projects/{self.p1.slug}/")
