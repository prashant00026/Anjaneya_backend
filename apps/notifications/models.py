from django.db import models


class FailedNotification(models.Model):
    """Persists email tasks that exhausted all retries.

    Inspecting `django-celery-results` only tells you a task failed;
    this row keeps the inputs needed to retry it from the admin.
    """

    subject = models.CharField(max_length=255)
    template_base = models.CharField(
        max_length=120,
        help_text="Template name without extension (e.g. 'emails/inquiry_property').",
    )
    recipients = models.TextField(
        help_text="Comma-separated list of recipient addresses.",
    )
    context_json = models.JSONField(default=dict, blank=True)
    from_email = models.CharField(max_length=255, blank=True)

    error_message = models.TextField(blank=True)
    last_retried_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "failed notification"
        verbose_name_plural = "failed notifications"

    def __str__(self):
        return f"{self.subject} → {self.recipients[:60]}"

    @property
    def recipient_list(self) -> list[str]:
        return [r.strip() for r in (self.recipients or "").split(",") if r.strip()]
