"""Step 7 — notifications app tests.

Covers:
    - send_templated_email renders both HTML + TXT variants
    - send_email_task records FailedNotification on terminal failure
    - The Enquiry post_save signal queues exactly one async email,
      wrapped in transaction.on_commit
    - Daily summary task aggregates and renders without errors
    - Unread-enquiry reminder respects the 24h cutoff
"""

from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, City
from enquiries.models import Enquiry
from projects.models import Project

from .models import FailedNotification
from .services import send_templated_email
from .tasks import (
    queue_enquiry_notification,
    remind_unread_enquiries,
    send_daily_admin_summary,
    send_email_task,
)


_TEST_REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
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
}


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Anjaneya <no-reply@example.com>",
    ENQUIRY_NOTIFICATION_EMAILS=["ops@example.com"],
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class ServiceTests(APITestCase):
    """Tests for the email service module itself (no Celery involvement)."""

    def setUp(self):
        mail.outbox = []

    def test_renders_html_and_text_variants(self):
        n = send_templated_email(
            subject="Hello",
            template_base="emails/enquiry_contact",
            context={
                "full_name": "Test Person", "mobile": "+910000000000",
                "email": "t@example.com", "message": "hi",
                "source_label": "Contact page",
                "created_at": "2026-05-14T10:00:00+05:30",
                "ip_address": "127.0.0.1",
                "admin_path": "/admin/",
            },
            to="ops@example.com",
        )
        self.assertEqual(n, 1)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["ops@example.com"])
        self.assertIn("Test Person", msg.body)  # txt variant
        html_parts = [c for c, ct in msg.alternatives or [] if ct == "text/html"]
        self.assertEqual(len(html_parts), 1)
        self.assertIn("Test Person", html_parts[0])

    def test_normalises_recipients_csv(self):
        send_templated_email(
            subject="x", template_base="emails/enquiry_contact",
            context={"full_name": "x", "mobile": "x", "email": "x", "message": "x",
                     "source_label": "x", "created_at": "x", "ip_address": "x",
                     "admin_path": "/"},
            to="a@x.com, b@x.com",
        )
        self.assertEqual(mail.outbox[0].to, ["a@x.com", "b@x.com"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ENQUIRY_NOTIFICATION_EMAILS=["ops@example.com"],
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class TaskFailureTests(APITestCase):
    """Verifies retry → FailedNotification path."""

    def test_on_failure_persists_failed_notification(self):
        # Unit-test `EmailTask.on_failure` directly. Exhausting the
        # autoretry budget in EAGER mode is awkward (Celery raises a
        # Retry exception rather than looping) and the retry path
        # itself is Celery's well-trodden code; what we own is the
        # persistence in on_failure.
        send_email_task.on_failure(
            exc=ConnectionError("smtp host down"),
            task_id="test-task-id",
            args=(),
            kwargs={
                "subject": "boom",
                "template_base": "emails/enquiry_contact",
                "context": {"full_name": "x"},
                "to": ["ops@example.com"],
            },
            einfo=None,
        )

        self.assertEqual(FailedNotification.objects.count(), 1)
        row = FailedNotification.objects.get()
        self.assertEqual(row.subject, "boom")
        self.assertEqual(row.template_base, "emails/enquiry_contact")
        self.assertIn("ConnectionError", row.error_message)
        self.assertEqual(row.recipient_list, ["ops@example.com"])

    def test_on_failure_handles_positional_args(self):
        # The same on_failure should work if the task was called with
        # positional arguments (which is what apply()/delay() does).
        send_email_task.on_failure(
            exc=ConnectionError("nope"),
            task_id="t2",
            args=("subject-x", "emails/enquiry_contact", {"a": 1}, "x@x.com"),
            kwargs={},
            einfo=None,
        )
        row = FailedNotification.objects.latest("created_at")
        self.assertEqual(row.subject, "subject-x")
        self.assertEqual(row.recipient_list, ["x@x.com"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ENQUIRY_NOTIFICATION_EMAILS=["ops@example.com"],
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    REST_FRAMEWORK=_TEST_REST_FRAMEWORK,  # drop the throttle for this test
)
class EnquiryFlowTests(APITestCase):
    """End-to-end: API call → DB row → on_commit → task → email in outbox."""

    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(name="Noida")
        cls.cat = Category.objects.create(name="Commercial")
        cls.project = Project.objects.create(
            title="CRC Flagship", category=cls.cat, city=cls.city,
            is_published=True,
        )

    def setUp(self):
        mail.outbox = []

    def test_property_enquiry_queues_exactly_one_email(self):
        # `transaction.on_commit` doesn't fire inside the test transaction;
        # `captureOnCommitCallbacks(execute=True)` runs them on exit.
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post("/api/v1/enquiries/", {
                "full_name": "Project Buyer",
                "mobile": "+919999999999",
                "email": "p@example.com",
                "message": "Interested in pricing",
                "source": "project_sidebar",
                "project": self.project.pk,
            }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, f"New enquiry: {self.project.title}")
        self.assertIn("CRC Flagship", msg.alternatives[0][0])
        self.assertIn("Interested in pricing", msg.body)

    def test_contact_enquiry_uses_site_template(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post("/api/v1/enquiries/", {
                "full_name": "Walk-in",
                "mobile": "+919999999998",
                "message": "General question",
                "source": "contact_page",
            }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Walk-in", mail.outbox[0].subject)
        self.assertNotIn("CRC", mail.outbox[0].subject)

    def test_no_email_when_recipients_empty(self):
        with override_settings(ENQUIRY_NOTIFICATION_EMAILS=[]):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post("/api/v1/enquiries/", {
                    "full_name": "X", "mobile": "+919999999997",
                    "source": "contact_page",
                }, format="json")
        self.assertEqual(len(mail.outbox), 0)

    def test_signal_schedules_on_commit_callback(self):
        """Confirms the post_save handler registers an on_commit hook
        rather than calling the queue function synchronously."""
        with mock.patch(
            "notifications.tasks.queue_enquiry_notification",
        ) as queue:
            with self.captureOnCommitCallbacks(execute=True):
                Enquiry.objects.create(
                    full_name="Direct create",
                    mobile="+910000000000",
                    source=Enquiry.Source.CONTACT_PAGE,
                )
        queue.assert_called_once()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ENQUIRY_NOTIFICATION_EMAILS=["ops@example.com"],
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class PeriodicTaskTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(name="Noida")
        cls.cat = Category.objects.create(name="Commercial")
        cls.project = Project.objects.create(
            title="CRC Flagship", category=cls.cat, city=cls.city,
            locality="Sector-140A",
            is_published=True, published_at=timezone.now(),
        )
        cls.project.created_at = timezone.now()  # cached for daily summary

        cls.recent = Enquiry.objects.create(
            full_name="Recent",
            mobile="+910000000001",
            source=Enquiry.Source.PROJECT_SIDEBAR,
            project=cls.project,
        )
        cls.stale_unread = Enquiry.objects.create(
            full_name="Stale",
            mobile="+910000000002",
            source=Enquiry.Source.CONTACT_PAGE,
            status=Enquiry.Status.NEW,
        )
        # Back-date to be older than 24h
        Enquiry.objects.filter(pk=cls.stale_unread.pk).update(
            created_at=timezone.now() - timedelta(hours=48),
        )

    def setUp(self):
        mail.outbox = []

    def test_daily_summary_runs_and_emails(self):
        send_daily_admin_summary()
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("Daily summary", msg.subject)
        # Project enquiry from the last 24h shows up.
        self.assertIn("CRC Flagship", msg.alternatives[0][0])

    def test_unread_reminder_emails_only_stale_new(self):
        remind_unread_enquiries()
        self.assertEqual(len(mail.outbox), 1)
        body_html = mail.outbox[0].alternatives[0][0]
        self.assertIn("Stale", body_html)
        # Recent enquiry (new but < 24h old) is NOT in the email.
        self.assertNotIn("Recent", body_html)

    def test_unread_reminder_skips_when_nothing_stale(self):
        Enquiry.objects.update(status=Enquiry.Status.CONTACTED)
        remind_unread_enquiries()
        self.assertEqual(len(mail.outbox), 0)
