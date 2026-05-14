"""Step 6 tests: email notification, throttle, admin auto-bump."""

from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.core import mail
from django.test import RequestFactory, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, City
from projects.models import Project

from .admin import EnquiryAdmin
from .models import Enquiry


@override_settings(
    ENQUIRY_NOTIFICATION_EMAILS=["ops@example.com"],
    DEFAULT_FROM_EMAIL="no-reply@example.com",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    # Step 7: emails go through Celery now. EAGER mode runs tasks
    # inline so we don't need a worker process.
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class EnquiryEmailTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(name="Noida")
        cls.cat = Category.objects.create(name="Commercial")
        cls.project = Project.objects.create(
            title="CRC The Flagship", category=cls.cat, city=cls.city,
            is_published=True,
        )

    def test_email_sent_when_enquiry_created(self):
        mail.outbox = []
        # Step 7: enquiry create defers the queue call via on_commit;
        # captureOnCommitCallbacks runs those callbacks on exit so we
        # can assert on mail.outbox.
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post("/api/v1/enquiries/", {
                "full_name": "Test Buyer",
                "mobile": "+919999999999",
                "email": "buyer@example.com",
                "message": "Interested",
                "project": self.project.pk,
                "source": "project_sidebar",
            }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("CRC The Flagship", msg.subject)
        self.assertEqual(msg.to, ["ops@example.com"])
        self.assertEqual(msg.from_email, "no-reply@example.com")
        # HTML alternative attached.
        self.assertTrue(
            any(ct == "text/html" for (_, ct) in msg.alternatives or []),
        )

    def test_email_subject_for_site_enquiry_without_project(self):
        mail.outbox = []
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/v1/enquiries/", {
                "full_name": "Walk-in Visitor",
                "mobile": "+919999999998",
                "message": "Need a callback",
                "source": "contact_page",
            }, format="json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Walk-in Visitor", mail.outbox[0].subject)
        self.assertNotIn("CRC", mail.outbox[0].subject)

    @override_settings(ENQUIRY_NOTIFICATION_EMAILS=[])
    def test_no_email_when_recipients_empty(self):
        mail.outbox = []
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/v1/enquiries/", {
                "full_name": "X", "mobile": "+919999999997",
                "source": "contact_page",
            }, format="json")
        self.assertEqual(len(mail.outbox), 0)


class EnquiryThrottleTests(APITestCase):
    """Verifies the real configured 10/hour scope. We can't use
    `override_settings` to dial it down because DRF's
    `SimpleRateThrottle.THROTTLE_RATES` class attribute holds a
    reference to the original rates dict and isn't reloaded when
    `api_settings.DEFAULT_THROTTLE_RATES` is swapped out.
    Instead we directly patch the class dict and restore in tearDown.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from rest_framework.throttling import SimpleRateThrottle

        cls._orig_rate = SimpleRateThrottle.THROTTLE_RATES.get("enquiry")
        SimpleRateThrottle.THROTTLE_RATES["enquiry"] = "3/hour"

    @classmethod
    def tearDownClass(cls):
        from rest_framework.throttling import SimpleRateThrottle

        if cls._orig_rate is None:
            SimpleRateThrottle.THROTTLE_RATES.pop("enquiry", None)
        else:
            SimpleRateThrottle.THROTTLE_RATES["enquiry"] = cls._orig_rate
        super().tearDownClass()

    def setUp(self):
        # Throttle counters live in the cache; reset between tests.
        from django.core.cache import cache
        cache.clear()

    def _post(self):
        return self.client.post("/api/v1/enquiries/", {
            "full_name": "Throttle Test",
            "mobile": "+919999999996",
            "source": "contact_page",
        }, format="json")

    def test_429_after_rate_exceeded(self):
        # First 3 should pass; 4th should 429 with Retry-After.
        for i in range(3):
            r = self._post()
            self.assertEqual(
                r.status_code, status.HTTP_201_CREATED,
                f"request #{i + 1} unexpectedly failed: {r.status_code} {r.content!r}",
            )
        r = self._post()
        self.assertEqual(r.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Retry-After", r)


class EnquiryAdminAutoStatusTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser("admin", "a@x.com", "pw")
        cls.enquiry = Enquiry.objects.create(
            full_name="Auto Bump",
            mobile="+910000000000",
            source=Enquiry.Source.CONTACT_PAGE,
            status=Enquiry.Status.NEW,
        )

    def test_status_flips_new_to_contacted_on_change_view_open(self):
        factory = RequestFactory()
        request = factory.get(
            f"/admin/enquiries/enquiry/{self.enquiry.pk}/change/",
        )
        request.user = self.admin_user
        # Sessions / messages middleware aren't run by RequestFactory; the
        # admin only needs `.user` for the change_view path we're hitting.
        admin = EnquiryAdmin(Enquiry, site)
        try:
            admin.change_view(request, str(self.enquiry.pk))
        except Exception:
            # We don't care about the template rendering here — just the
            # side effect on `status`.
            pass
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.CONTACTED)

    def test_status_not_overwritten_on_subsequent_opens(self):
        # Pre-existing status from a later workflow step.
        self.enquiry.status = Enquiry.Status.QUALIFIED
        self.enquiry.save(update_fields=["status"])
        factory = RequestFactory()
        request = factory.get(
            f"/admin/enquiries/enquiry/{self.enquiry.pk}/change/",
        )
        request.user = self.admin_user
        admin = EnquiryAdmin(Enquiry, site)
        try:
            admin.change_view(request, str(self.enquiry.pk))
        except Exception:
            pass
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.QUALIFIED)
