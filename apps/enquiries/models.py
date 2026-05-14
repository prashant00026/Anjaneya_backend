from django.db import models
from simple_history.models import HistoricalRecords


class Enquiry(models.Model):
    class Source(models.TextChoices):
        CONTACT_PAGE = "contact_page", "Contact page"
        PROJECT_SIDEBAR = "project_sidebar", "Project sidebar"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        CLOSED = "closed", "Closed"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="enquiries",
    )
    full_name = models.CharField(max_length=120)
    mobile = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    message = models.TextField(blank=True)

    source = models.CharField(
        max_length=24, choices=Source.choices, default=Source.CONTACT_PAGE,
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.NEW,
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    # Step 8: admin-only follow-up tracking. None of these are exposed
    # on the public API — they live for staff workflow.
    internal_notes = models.TextField(
        blank=True,
        help_text="Staff-only notes about follow-up calls, context, etc.",
    )
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    contacted_by = models.CharField(
        max_length=150, blank=True,
        help_text="Username of the admin who last marked this contacted.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "enquiries"
        indexes = [
            models.Index(fields=("status", "created_at")),
        ]

    def __str__(self):
        target = self.project.title if self.project_id else "site"
        return f"{self.full_name} ({self.mobile}) — {target}"
