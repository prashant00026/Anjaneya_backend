import csv
import re

from django.contrib import admin as django_admin
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from import_export.admin import ExportActionMixin
from import_export import resources
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm
from unfold.decorators import action as unfold_action
from unfold.decorators import display as unfold_display

from .models import Enquiry


class EnquiryResource(resources.ModelResource):
    class Meta:
        model = Enquiry
        fields = (
            "id", "created_at", "source", "status", "full_name",
            "mobile", "email", "project__title", "message",
            "internal_notes", "last_contacted_at", "contacted_by",
            "ip_address",
        )
        export_order = fields


def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


@django_admin.register(Enquiry)
class EnquiryAdmin(SimpleHistoryAdmin, ExportActionMixin, ModelAdmin):
    """Enquiries get touched dozens of times a day — make the screen fast.

    The list view exposes one-tap call / WhatsApp links, a click-through
    to the linked project, and a "Mark as contacted" action that stamps
    `last_contacted_at` + `contacted_by`.
    """

    resource_class = EnquiryResource
    export_form_class = ExportForm

    list_display = (
        "created_at", "status", "full_name",
        "phone_clickable", "project_link",
        "source", "last_contacted_at_short",
    )
    list_filter = ("status", "source", "created_at")
    list_editable = ("status",)
    list_per_page = 25
    list_select_related = ("project",)
    search_fields = ("full_name", "mobile", "email", "message")
    autocomplete_fields = ("project",)
    readonly_fields = (
        "ip_address", "user_agent",
        "created_at", "updated_at",
        "last_contacted_at", "contacted_by",
    )
    date_hierarchy = "created_at"
    save_on_top = True
    fieldsets = (
        (None, {"fields": ("project", "full_name", "mobile", "email", "message")}),
        ("Routing", {"fields": ("source", "status")}),
        ("Follow-up (admin only)", {
            "fields": ("internal_notes", "last_contacted_at", "contacted_by"),
        }),
        ("Audit", {
            "fields": ("ip_address", "user_agent", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    actions = ("mark_as_contacted",)

    # ---- Display callables ------------------------------------------------

    @unfold_display(description="Phone")
    def phone_clickable(self, obj):
        if not obj.mobile:
            return "—"
        tel = obj.mobile
        wa = _digits_only(obj.mobile)
        return format_html(
            '<a href="tel:{}">{}</a> · '
            '<a href="https://wa.me/{}" target="_blank">WhatsApp</a>',
            tel, tel, wa,
        )

    @unfold_display(description="Project", ordering="project__title")
    def project_link(self, obj):
        if not obj.project_id:
            return "—"
        url = reverse("admin:projects_project_change", args=[obj.project_id])
        return format_html('<a href="{}">{}</a>', url, obj.project.title)

    @unfold_display(description="Contacted", ordering="last_contacted_at")
    def last_contacted_at_short(self, obj):
        if not obj.last_contacted_at:
            return "—"
        by = f" by {obj.contacted_by}" if obj.contacted_by else ""
        return f"{obj.last_contacted_at.strftime('%Y-%m-%d %H:%M')}{by}"

    # ---- Auto-bump status on first open ----------------------------------

    def change_view(self, request, object_id, form_url="", extra_context=None):
        # Treat opening the detail as "I've seen this" — flip new → contacted.
        try:
            obj = self.get_object(request, object_id)
            if obj and obj.status == Enquiry.Status.NEW:
                Enquiry.objects.filter(pk=obj.pk, status=Enquiry.Status.NEW).update(
                    status=Enquiry.Status.CONTACTED,
                    last_contacted_at=timezone.now(),
                    contacted_by=request.user.username or "",
                )
        except Exception:
            pass
        return super().change_view(request, object_id, form_url, extra_context)

    # ---- Bulk actions ----------------------------------------------------

    @unfold_action(description="Mark selected as contacted")
    def mark_as_contacted(self, request, queryset):
        updated = queryset.update(
            status=Enquiry.Status.CONTACTED,
            last_contacted_at=timezone.now(),
            contacted_by=request.user.username or "",
        )
        self.message_user(
            request, f"Marked {updated} enquiry(ies) as contacted.",
            level=messages.SUCCESS,
        )

    # The CSV export kept from step 6 — kept alongside import-export's
    # native exporter (which lives behind the "Export" button at the top
    # right) so admins can grab a quick CSV via the actions dropdown too.
    @unfold_action(description="Export selected to CSV (quick)")
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="enquiries.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            "id", "created_at", "source", "status",
            "full_name", "mobile", "email",
            "project", "message", "internal_notes",
            "last_contacted_at", "contacted_by", "ip_address",
        ])
        for e in queryset.select_related("project"):
            writer.writerow([
                e.id, e.created_at.isoformat(timespec="seconds"),
                e.get_source_display(), e.get_status_display(),
                e.full_name, e.mobile, e.email,
                e.project.title if e.project_id else "",
                (e.message or "").replace("\n", " ").strip(),
                (e.internal_notes or "").replace("\n", " ").strip(),
                e.last_contacted_at.isoformat(timespec="seconds") if e.last_contacted_at else "",
                e.contacted_by or "",
                e.ip_address or "",
            ])
        return response
