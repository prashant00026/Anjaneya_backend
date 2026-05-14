"""Step 8 — admin smoke tests.

Confirms:
- Every admin changelist loads under a logged-in superuser
- Every admin change form loads for an existing row
- Custom Project actions (publish / unpublish / feature / duplicate)
- View-on-site link surfaces only when is_published
- Enquiry status auto-flip stamps contacted_by and last_contacted_at
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, City
from enquiries.models import Enquiry

from .models import Project


class AdminSmokeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", "a@x.com", "pw")
        cls.city = City.objects.create(name="Noida")
        cls.cat = Category.objects.create(name="Commercial")
        cls.project = Project.objects.create(
            title="CRC The Flagship", category=cls.cat, city=cls.city,
            locality="Sector-140A", is_published=True, is_featured=True,
        )
        cls.draft = Project.objects.create(
            title="Draft Project", category=cls.cat, city=cls.city,
            is_published=False,
        )
        cls.enquiry = Enquiry.objects.create(
            full_name="Test Caller",
            mobile="+919999999999",
            project=cls.project,
            source=Enquiry.Source.PROJECT_SIDEBAR,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    # ---- Changelist + change-form smoke ----------------------------------

    def _smoke(self, url_name, *args):
        url = reverse(url_name, args=args)
        r = self.client.get(url)
        self.assertIn(
            r.status_code, (200, 302),
            f"{url_name} → {r.status_code} unexpectedly",
        )

    def test_project_admin_pages_load(self):
        self._smoke("admin:projects_project_changelist")
        self._smoke("admin:projects_project_change", self.project.pk)

    def test_enquiry_admin_pages_load(self):
        self._smoke("admin:enquiries_enquiry_changelist")
        self._smoke("admin:enquiries_enquiry_change", self.enquiry.pk)

    def test_catalog_admin_pages_load(self):
        self._smoke("admin:catalog_city_changelist")
        self._smoke("admin:catalog_category_changelist")
        self._smoke("admin:catalog_developer_changelist")
        self._smoke("admin:catalog_amenity_changelist")

    def test_other_admin_pages_load(self):
        self._smoke("admin:team_teammember_changelist")
        self._smoke("admin:testimonials_testimonial_changelist")
        self._smoke("admin:site_settings_cmspage_changelist")
        self._smoke("admin:notifications_failednotification_changelist")

    def test_admin_index_runs_dashboard_callback(self):
        r = self.client.get(reverse("admin:index"))
        self.assertEqual(r.status_code, 200)
        # Our dashboard callback injects these keys.
        self.assertIn("dashboard_cards", r.context)
        self.assertIn("recent_projects", r.context)
        self.assertIn("recent_enquiries", r.context)
        # Sanity: counts are non-negative ints.
        for card in r.context["dashboard_cards"]:
            self.assertGreaterEqual(int(card["value"]), 0)

    # ---- Project actions -------------------------------------------------

    def _action(self, action_name, ids):
        return self.client.post(
            reverse("admin:projects_project_changelist"),
            data={
                "action": action_name,
                "_selected_action": [str(i) for i in ids],
            },
            follow=True,
        )

    def test_publish_action_flips_draft_to_published(self):
        r = self._action("publish_selected", [self.draft.pk])
        self.assertEqual(r.status_code, 200)
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.is_published)
        self.assertIsNotNone(self.draft.published_at)

    def test_unpublish_action(self):
        r = self._action("unpublish_selected", [self.project.pk])
        self.assertEqual(r.status_code, 200)
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_published)

    def test_feature_action(self):
        r = self._action("feature_selected", [self.draft.pk])
        self.assertEqual(r.status_code, 200)
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.is_featured)

    def test_duplicate_action_creates_unpublished_copy(self):
        before = Project.objects.count()
        r = self._action("duplicate_listing", [self.project.pk])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Project.objects.count(), before + 1)
        copy = Project.objects.exclude(pk=self.project.pk).filter(
            title__icontains="(Copy)",
        ).get()
        self.assertFalse(copy.is_published)
        self.assertFalse(copy.is_featured)
        self.assertNotEqual(copy.slug, self.project.slug)

    # ---- View-on-site + recent enquiries on change form ------------------

    def test_change_form_exposes_view_on_site_when_published(self):
        url = reverse("admin:projects_project_change", args=[self.project.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.context.get("view_on_site_url"),
            f"/api/v1/projects/{self.project.slug}/",
        )
        # Recent enquiries are exposed too.
        recent = r.context.get("recent_enquiries", [])
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].pk, self.enquiry.pk)

    def test_change_form_hides_view_on_site_when_draft(self):
        url = reverse("admin:projects_project_change", args=[self.draft.pk])
        r = self.client.get(url)
        self.assertIsNone(r.context.get("view_on_site_url"))

    # ---- Enquiry status auto-flip ----------------------------------------

    def test_enquiry_change_view_stamps_contacted_by(self):
        url = reverse("admin:enquiries_enquiry_change", args=[self.enquiry.pk])
        self.client.get(url)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.CONTACTED)
        self.assertEqual(self.enquiry.contacted_by, self.admin.username)
        self.assertIsNotNone(self.enquiry.last_contacted_at)
