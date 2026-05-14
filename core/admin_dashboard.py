"""Custom admin index dashboard for django-unfold.

Returns the extra context Unfold injects into its dashboard template.
Keep it cheap: every staff login opens this page.
"""

from __future__ import annotations

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone


def dashboard_callback(request, context):
    """Populate `context` with counts + recent lists for the admin index."""
    from enquiries.models import Enquiry
    from projects.models import Project

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    projects_qs = Project.objects.all()
    enquiries_qs = Enquiry.objects.all()

    cards = [
        {
            "title": "Total projects",
            "value": projects_qs.count(),
            "detail": f"{projects_qs.filter(is_published=True).count()} published",
            "link": reverse("admin:projects_project_changelist"),
        },
        {
            "title": "Featured",
            "value": projects_qs.filter(is_featured=True, is_published=True).count(),
            "detail": "homepage row",
            "link": reverse("admin:projects_project_changelist") + "?is_featured__exact=1",
        },
        {
            "title": "New enquiries · today",
            "value": enquiries_qs.filter(created_at__gte=today_start).count(),
            "detail": f"{enquiries_qs.filter(created_at__gte=week_start).count()} this week",
            "link": reverse("admin:enquiries_enquiry_changelist"),
        },
        {
            "title": "Unread enquiries",
            "value": enquiries_qs.filter(status=Enquiry.Status.NEW).count(),
            "detail": "status = new",
            "link": (
                reverse("admin:enquiries_enquiry_changelist") + "?status__exact=new"
            ),
        },
    ]

    recent_projects = list(
        projects_qs.select_related("city", "category")
        .order_by("-created_at")[:10]
    )
    recent_enquiries = list(
        enquiries_qs.select_related("project")
        .order_by("-created_at")[:10]
    )

    context.update({
        "dashboard_cards": cards,
        "recent_projects": recent_projects,
        "recent_enquiries": recent_enquiries,
    })
    return context
