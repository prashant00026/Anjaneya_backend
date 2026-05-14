import io
import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, City

from .models import FloorPlan, Project, ProjectImage


# ---- helpers ---------------------------------------------------------------

def _png(width=600, height=400, color=(255, 0, 0)) -> bytes:
    """Build a valid PNG byte payload at the requested dimensions."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _pdf() -> bytes:
    """Minimal valid PDF body."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n110\n%%EOF"
    )


_TMP_MEDIA = tempfile.mkdtemp(prefix="anjaneya_test_media_")


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class ProjectMediaTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(name="Noida")
        cls.cat = Category.objects.create(name="Commercial")
        cls.project = Project.objects.create(
            title="CRC The Flagship",
            category=cls.cat, city=cls.city,
            locality="Sector-140A",
            is_published=True, is_featured=True,
        )
        cls.admin = User.objects.create_superuser("admin", "a@x.com", "pw")
        cls.staff = User.objects.create_user("staff", "s@x.com", "pw")  # non-admin

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TMP_MEDIA, ignore_errors=True)

    # ---------------- Public read ------------------------------------------

    def test_list_published_returns_lightweight_shape(self):
        r = self.client.get("/api/v1/projects/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        result = r.data["results"][0]
        # Light shape: no description, no full size variants
        self.assertIn("image_count", result)
        self.assertNotIn("description", result)
        self.assertNotIn("cover_large", result)

    def test_detail_includes_floor_plans_field(self):
        r = self.client.get(f"/api/v1/projects/{self.project.slug}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("floor_plans", r.data)
        self.assertIn("images", r.data)

    # ---------------- Upload happy-path ------------------------------------

    def _upload(self, url, file_field, name, body, content_type="image/png"):
        return self.client.post(
            url,
            data={file_field: SimpleUploadedFile(name, body, content_type=content_type)},
            format="multipart",
        )

    def test_valid_image_upload_returns_201(self):
        self.client.force_authenticate(self.admin)
        r = self._upload(
            f"/api/v1/projects/{self.project.pk}/images/",
            "image", "ok.png", _png(),
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(self.project.images.count(), 1)
        # File actually landed on disk
        img = self.project.images.first()
        self.assertTrue(os.path.exists(img.image.path))

    def test_anonymous_upload_is_forbidden(self):
        r = self._upload(
            f"/api/v1/projects/{self.project.pk}/images/",
            "image", "ok.png", _png(),
        )
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertEqual(self.project.images.count(), 0)

    def test_non_admin_authenticated_user_is_forbidden(self):
        self.client.force_authenticate(self.staff)
        r = self._upload(
            f"/api/v1/projects/{self.project.pk}/images/",
            "image", "ok.png", _png(),
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    # ---------------- Upload validation ------------------------------------

    def test_oversized_image_rejected(self):
        self.client.force_authenticate(self.admin)
        with override_settings(MAX_IMAGE_SIZE_MB=0.001):  # ~1 KB cap
            r = self._upload(
                f"/api/v1/projects/{self.project.pk}/images/",
                "image", "big.png", _png(),
            )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exe_renamed_as_jpg_rejected_by_mime_sniff(self):
        self.client.force_authenticate(self.admin)
        bogus = b"MZ\x90\x00" + b"\x00" * 1024  # PE header bytes
        r = self._upload(
            f"/api/v1/projects/{self.project.pk}/images/",
            "image", "evil.jpg", bogus, content_type="image/jpeg",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_below_min_dimensions_rejected(self):
        self.client.force_authenticate(self.admin)
        r = self._upload(
            f"/api/v1/projects/{self.project.pk}/images/",
            "image", "tiny.png", _png(100, 100),
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------------- Primary invariant ------------------------------------

    def test_setting_primary_unsets_others(self):
        self.client.force_authenticate(self.admin)
        a = ProjectImage.objects.create(
            project=self.project,
            image=SimpleUploadedFile("a.png", _png(), "image/png"),
            is_primary=True, display_order=1,
        )
        b = ProjectImage.objects.create(
            project=self.project,
            image=SimpleUploadedFile("b.png", _png(), "image/png"),
            is_primary=True, display_order=2,
        )
        a.refresh_from_db(); b.refresh_from_db()
        self.assertFalse(a.is_primary)
        self.assertTrue(b.is_primary)
        # Manager.primary() returns the flagged one.
        self.assertEqual(self.project.images.primary(), b)

    def test_primary_manager_falls_back_to_first_by_order_when_none_flagged(self):
        a = ProjectImage.objects.create(
            project=self.project,
            image=SimpleUploadedFile("a.png", _png(), "image/png"),
            display_order=2,
        )
        b = ProjectImage.objects.create(
            project=self.project,
            image=SimpleUploadedFile("b.png", _png(), "image/png"),
            display_order=1,
        )
        self.assertEqual(self.project.images.primary(), b)

    # ---------------- Floor plans (image + PDF) ----------------------------

    def test_floor_plan_pdf_accepted(self):
        self.client.force_authenticate(self.admin)
        r = self._upload(
            f"/api/v1/projects/{self.project.pk}/floor-plans/",
            "file", "ground.pdf", _pdf(), content_type="application/pdf",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(self.project.floor_plans.count(), 1)

    def test_floor_plan_image_accepted(self):
        self.client.force_authenticate(self.admin)
        r = self._upload(
            f"/api/v1/projects/{self.project.pk}/floor-plans/",
            "file", "ground.png", _png(800, 600), content_type="image/png",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)

    def test_floor_plan_size_limit(self):
        self.client.force_authenticate(self.admin)
        with override_settings(MAX_FLOOR_PLAN_SIZE_MB=0.001):
            r = self._upload(
                f"/api/v1/projects/{self.project.pk}/floor-plans/",
                "file", "big.png", _png(), content_type="image/png",
            )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------------- Cascade + file cleanup -------------------------------

    def test_delete_project_removes_files_from_disk(self):
        img = ProjectImage.objects.create(
            project=self.project,
            image=SimpleUploadedFile("c.png", _png(), "image/png"),
        )
        path = img.image.path
        self.assertTrue(os.path.exists(path))
        self.project.delete()
        self.assertFalse(os.path.exists(path))

    def test_delete_image_removes_file(self):
        img = ProjectImage.objects.create(
            project=self.project,
            image=SimpleUploadedFile("d.png", _png(), "image/png"),
        )
        path = img.image.path
        self.assertTrue(os.path.exists(path))
        img.delete()
        self.assertFalse(os.path.exists(path))

    # ---------------- Serializer URLs --------------------------------------

    def test_detail_response_returns_absolute_image_urls(self):
        ProjectImage.objects.create(
            project=self.project,
            image=SimpleUploadedFile("e.png", _png(), "image/png"),
            is_primary=True, alt_text="A test image",
        )
        r = self.client.get(f"/api/v1/projects/{self.project.slug}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        first = r.data["images"][0]
        self.assertTrue(first["image"].startswith("http://"))
        # Thumbnail spec field also resolves to a URL.
        self.assertTrue(first["thumbnail"].startswith("http://"))
        self.assertEqual(first["alt_text"], "A test image")

    # ---------------- Filter / search regression ---------------------------

    def test_list_by_category_slug_still_works(self):
        r = self.client.get("/api/v1/projects/", {"category": "commercial"})
        self.assertEqual(r.data["count"], 1)
