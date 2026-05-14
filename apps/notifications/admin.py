from datetime import timedelta

from django import forms
from django.contrib import admin as django_admin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import FailedNotification
from .tasks import send_email_task


@django_admin.register(FailedNotification)
class FailedNotificationAdmin(ModelAdmin):
    list_display = (
        "created_at", "subject", "recipients_short", "template_base",
        "last_retried_at",
    )
    list_filter = ("template_base", "created_at")
    search_fields = ("subject", "recipients", "error_message")
    readonly_fields = (
        "subject", "template_base", "recipients", "context_json",
        "from_email", "error_message", "last_retried_at", "created_at",
    )
    actions = ("retry_send",)
    date_hierarchy = "created_at"

    @django_admin.display(description="Recipients")
    def recipients_short(self, obj):
        return (obj.recipients or "")[:80]

    @django_admin.action(description="Retry sending the selected notifications")
    def retry_send(self, request, queryset):
        sent = 0
        for row in queryset:
            send_email_task.delay(
                subject=row.subject,
                template_base=row.template_base,
                context=row.context_json or {},
                to=row.recipient_list,
                from_email=row.from_email or None,
            )
            row.last_retried_at = timezone.now()
            row.save(update_fields=["last_retried_at"])
            sent += 1
        self.message_user(
            request, f"Re-queued {sent} notification(s).",
            level=messages.SUCCESS,
        )

    # ---- Test-email tool -------------------------------------------------
    # A small admin page that lets staff queue a sample email to verify
    # SMTP config without faking an enquiry. Visible to users with
    # `notifications.view_failednotification` permission (i.e. any staff
    # who can see this admin section).

    def get_urls(self):
        return [
            path(
                "test-email/",
                self.admin_site.admin_view(self.test_email_view),
                name="notifications_test_email",
            ),
        ] + super().get_urls()

    def test_email_view(self, request):
        if request.method == "POST":
            form = TestEmailForm(request.POST)
            if form.is_valid():
                template = form.cleaned_data["template"]
                to = form.cleaned_data["to"]
                send_email_task.delay(
                    subject=f"[TEST] {template}",
                    template_base=f"emails/{template}",
                    context=_sample_context_for(template),
                    to=[to],
                )
                self.message_user(
                    request, f"Test email queued to {to}.",
                    level=messages.SUCCESS,
                )
                return redirect(
                    "admin:notifications_failednotification_changelist",
                )
        else:
            form = TestEmailForm()

        return render(request, "admin/notifications/test_email.html", {
            "title": "Send test email",
            "form": form,
            "opts": self.model._meta,
        })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["test_email_url"] = format_html(
            '<a href="test-email/">Send test email</a>',
        )
        return super().changelist_view(request, extra_context)


class TestEmailForm(forms.Form):
    TEMPLATE_CHOICES = (
        ("enquiry_property", "Enquiry — property"),
        ("enquiry_contact", "Enquiry — site contact"),
        ("daily_summary", "Daily summary"),
        ("unread_reminder", "Unread reminder"),
    )
    to = forms.EmailField(label="Send to")
    template = forms.ChoiceField(label="Template", choices=TEMPLATE_CHOICES)


def _sample_context_for(template: str) -> dict:
    """Plausible context for the test-email tool so the templates render."""
    if template in ("enquiry_property", "enquiry_contact"):
        return {
            "full_name": "Test Person",
            "mobile": "+919999999999",
            "email": "test@example.com",
            "message": "Sample enquiry message for SMTP smoke test.",
            "project_title": "Sample Project" if template == "enquiry_property" else None,
            "source_label": "Project sidebar" if template == "enquiry_property" else "Contact page",
            "created_at": timezone.now().isoformat(),
            "ip_address": "127.0.0.1",
            "admin_path": "/admin/",
            "enquiry_id": 0,
        }
    if template == "daily_summary":
        return {
            "since": timezone.now() - timedelta(days=1),
            "now": timezone.now(),
            "site_enquiries_count": 2,
            "project_enquiries_count": 5,
            "new_projects_count": 1,
            "top_projects": [{"project__title": "Sample Project", "c": 4}],
            "top_localities": [{"project__locality": "Sector-140A", "c": 3}],
        }
    if template == "unread_reminder":
        return {
            "count": 2,
            "cutoff": timezone.now() - timedelta(hours=24),
            "enquiries": [
                {"id": 101, "name": "Alex", "mobile": "+910000000001",
                 "project_title": "Sample Project",
                 "source": "Project sidebar",
                 "created_at": timezone.now()},
                {"id": 102, "name": "Beth", "mobile": "+910000000002",
                 "project_title": None,
                 "source": "Contact page",
                 "created_at": timezone.now()},
            ],
        }
    return {}
