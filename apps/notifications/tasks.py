"""Celery tasks: email send + periodic admin notifications.

`send_email_task` is the universal "send mail" entrypoint:
    send_email_task.delay(
        subject="…",
        template_base="emails/inquiry_property",
        context={…},
        to=["ops@example.com"],
    )

Retries with exponential backoff (60s, 120s, 240s, 480s, 600s capped).
After max_retries the inputs land in `FailedNotification` so admin can
inspect + manually retry from /admin/.
"""

from __future__ import annotations

import logging
import socket
from datetime import timedelta
from smtplib import SMTPException

from celery import Task, shared_task
from django.utils import timezone


log = logging.getLogger(__name__)


_RETRYABLE_EXCEPTIONS = (SMTPException, ConnectionError, socket.error, OSError, TimeoutError)


class EmailTask(Task):
    """Records FailedNotification rows when an email task gives up.

    Celery only invokes `on_failure` after the task exhausts its
    autoretry budget (or raises a non-retryable exception). This is
    the right hook for terminal failures — wrapping a try/except
    inside the task body doesn't work in EAGER mode because the retry
    mechanism re-raises outside the function.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from .models import FailedNotification

        subject = kwargs.get("subject") or (args[0] if args else "")
        template_base = kwargs.get("template_base") or (args[1] if len(args) > 1 else "")
        context = kwargs.get("context") or (args[2] if len(args) > 2 else {})
        to = kwargs.get("to") or (args[3] if len(args) > 3 else "")
        from_email = kwargs.get("from_email") or (args[4] if len(args) > 4 else "")

        recipients = ", ".join(
            to if isinstance(to, (list, tuple))
            else [t.strip() for t in str(to).split(",") if t.strip()]
        )
        try:
            FailedNotification.objects.create(
                subject=subject,
                template_base=template_base,
                recipients=recipients,
                context_json=context or {},
                from_email=from_email or "",
                error_message=f"{type(exc).__name__}: {exc}",
            )
        except Exception:
            log.exception(
                "Failed to persist FailedNotification (task=%s id=%s subject=%s)",
                self.name, task_id, subject,
            )


@shared_task(
    base=EmailTask,
    bind=True,
    autoretry_for=_RETRYABLE_EXCEPTIONS,
    retry_backoff=60,           # start at 60s
    retry_backoff_max=600,      # cap at 10 minutes
    retry_jitter=True,
    max_retries=5,
)
def send_email_task(
    self,
    subject: str,
    template_base: str,
    context: dict,
    to,
    from_email: str | None = None,
):
    """Send a templated email. Retries on infra errors; terminal failures
    land in FailedNotification via `EmailTask.on_failure`."""
    # Lazy import — Celery autodiscover scans this module on app boot.
    from .services import send_templated_email

    return send_templated_email(
        subject=subject, template_base=template_base,
        context=context, to=to, from_email=from_email,
    )


# ---------------------------------------------------------------------------
# Periodic tasks
# ---------------------------------------------------------------------------

@shared_task
def send_daily_admin_summary():
    """Daily roll-up email to INQUIRY_NOTIFICATION_EMAILS."""
    from django.conf import settings as dj_settings
    from django.db.models import Count

    from enquiries.models import Enquiry
    from projects.models import Project

    recipients = list(getattr(dj_settings, "INQUIRY_NOTIFICATION_EMAILS", []) or [])
    if not recipients:
        log.info("Skipping daily summary: INQUIRY_NOTIFICATION_EMAILS empty.")
        return

    since = timezone.now() - timedelta(days=1)

    enq_qs = Enquiry.objects.filter(created_at__gte=since)
    site_enq = enq_qs.filter(source=Enquiry.Source.CONTACT_PAGE).count()
    project_enq_qs = enq_qs.filter(project__isnull=False)
    project_enq_count = project_enq_qs.count()

    top_projects = list(
        project_enq_qs.values("project__title")
        .annotate(c=Count("id"))
        .order_by("-c")[:5]
    )
    top_localities = list(
        project_enq_qs.exclude(project__locality="")
        .values("project__locality")
        .annotate(c=Count("id"))
        .order_by("-c")[:5]
    )

    new_projects = Project.objects.filter(
        created_at__gte=since, is_published=True,
    ).count()

    ctx = {
        "since": since,
        "now": timezone.now(),
        "site_enquiries_count": site_enq,
        "project_enquiries_count": project_enq_count,
        "top_projects": top_projects,
        "top_localities": top_localities,
        "new_projects_count": new_projects,
    }
    send_email_task.delay(
        subject=f"Daily summary — {since.date().isoformat()} → {timezone.now().date().isoformat()}",
        template_base="emails/daily_summary",
        context=ctx,
        to=recipients,
    )


@shared_task
def remind_unread_inquiries():
    """If any enquiry older than 24h is still `status=new`, send a nag email."""
    from django.conf import settings as dj_settings

    from enquiries.models import Enquiry

    recipients = list(getattr(dj_settings, "INQUIRY_NOTIFICATION_EMAILS", []) or [])
    if not recipients:
        return

    cutoff = timezone.now() - timedelta(hours=24)
    stale = list(
        Enquiry.objects.filter(
            status=Enquiry.Status.NEW, created_at__lt=cutoff,
        ).select_related("project").order_by("created_at")[:25]
    )
    if not stale:
        return

    ctx = {
        "count": len(stale),
        "enquiries": [
            {
                "id": e.id,
                "name": e.full_name,
                "mobile": e.mobile,
                "project_title": e.project.title if e.project_id else None,
                "source": e.get_source_display(),
                "created_at": e.created_at,
            }
            for e in stale
        ],
        "cutoff": cutoff,
    }
    send_email_task.delay(
        subject=f"Reminder: {len(stale)} unread inquiry(ies) older than 24 hours",
        template_base="emails/unread_reminder",
        context=ctx,
        to=recipients,
    )


# ---------------------------------------------------------------------------
# Wrapper used by apps/enquiries/apps.py to queue the right email per source.
# ---------------------------------------------------------------------------

def queue_inquiry_notification(enquiry):
    """Build context + queue the email task. Caller is expected to wrap in
    `transaction.on_commit(...)` if invoked inside a DB transaction.
    """
    from django.conf import settings as dj_settings
    from django.urls import reverse

    recipients = list(getattr(dj_settings, "INQUIRY_NOTIFICATION_EMAILS", []) or [])
    if not recipients:
        return

    project_title = enquiry.project.title if enquiry.project_id else None
    if project_title:
        template = "emails/inquiry_property"
        subject = f"New inquiry: {project_title}"
    else:
        template = "emails/inquiry_contact"
        subject = f"New site enquiry from {enquiry.full_name}"

    try:
        admin_path = reverse(
            "admin:enquiries_enquiry_change", args=[enquiry.pk],
        )
    except Exception:
        admin_path = f"/admin/enquiries/enquiry/{enquiry.pk}/change/"

    ctx = {
        "enquiry_id": enquiry.pk,
        "full_name": enquiry.full_name,
        "mobile": enquiry.mobile,
        "email": enquiry.email,
        "message": enquiry.message,
        "project_title": project_title,
        "source_label": enquiry.get_source_display(),
        "created_at": enquiry.created_at.isoformat() if enquiry.created_at else None,
        "ip_address": enquiry.ip_address,
        "admin_path": admin_path,
    }
    send_email_task.delay(
        subject=subject, template_base=template,
        context=ctx, to=recipients,
    )
