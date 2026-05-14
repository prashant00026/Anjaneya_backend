from decimal import Decimal

from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from unfold.decorators import action as unfold_action
from unfold.decorators import display as unfold_display

from .models import (
    FloorPlan,
    Project,
    ProjectHighlight,
    ProjectImage,
    ProjectStat,
)


# ---------------------------------------------------------------------------
# Inlines (Unfold-themed)
# ---------------------------------------------------------------------------

class ProjectImageInline(TabularInline):
    model = ProjectImage
    extra = 0
    fields = ("preview", "image", "caption", "alt_text", "display_order", "is_primary")
    readonly_fields = ("preview",)
    ordering = ("display_order", "id")

    @unfold_display(description="Preview")
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return "—"
        try:
            url = obj.thumbnail.url
        except Exception:
            url = obj.image.url
        return format_html(
            '<img src="{}" style="height:80px;width:auto;border-radius:4px"/>',
            url,
        )


class FloorPlanInline(TabularInline):
    model = FloorPlan
    extra = 0
    fields = ("preview", "file", "label", "caption", "alt_text", "display_order")
    readonly_fields = ("preview",)
    ordering = ("display_order", "id")

    @unfold_display(description="Preview")
    def preview(self, obj):
        if not obj.pk or not obj.file:
            return "—"
        url = obj.file.url
        if url.lower().endswith(".pdf"):
            return format_html('<a href="{}" target="_blank">PDF</a>', url)
        return format_html(
            '<img src="{}" style="height:80px;width:auto;border-radius:4px"/>',
            url,
        )


class ProjectHighlightInline(TabularInline):
    model = ProjectHighlight
    extra = 0
    fields = ("text", "display_order")


class ProjectStatInline(TabularInline):
    model = ProjectStat
    extra = 0
    fields = ("label", "value", "icon_key", "display_order")


# ---------------------------------------------------------------------------
# Bulk-upload form
# ---------------------------------------------------------------------------

class _MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class _MultiFileField(forms.FileField):
    widget = _MultiFileInput

    def to_python(self, data):
        if data in self.empty_values:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        for f in data:
            super().to_python(f)
        return list(data)


class BulkImageUploadForm(forms.Form):
    images = _MultiFileField(label="Select images")


# ---------------------------------------------------------------------------
# import-export Resource
# ---------------------------------------------------------------------------

class ProjectResource(resources.ModelResource):
    """CSV/XLSX import-export. FKs resolve by slug so spreadsheets stay readable."""

    category = resources.Field(
        attribute="category", column_name="category_slug",
        widget=resources.widgets.ForeignKeyWidget(
            __import__("catalog", fromlist=["models"]).models.Category, "slug",
        ),
    )
    city = resources.Field(
        attribute="city", column_name="city_slug",
        widget=resources.widgets.ForeignKeyWidget(
            __import__("catalog", fromlist=["models"]).models.City, "slug",
        ),
    )
    developer = resources.Field(
        attribute="developer", column_name="developer_slug",
        widget=resources.widgets.ForeignKeyWidget(
            __import__("catalog", fromlist=["models"]).models.Developer, "slug",
        ),
    )

    class Meta:
        model = Project
        import_id_fields = ("slug",)
        fields = (
            "id", "slug", "title", "tagline", "category", "city", "locality",
            "developer", "status", "property_type",
            "price_starting_lacs", "price_display", "size_display",
            "rera_number", "is_featured", "featured_order",
            "is_published", "published_at", "created_at",
        )
        export_order = fields


# ---------------------------------------------------------------------------
# Project admin
# ---------------------------------------------------------------------------

def _format_indian_price_lacs(value: Decimal | None) -> str:
    """Render price (stored in lakhs) as "₹ 80 L" or "₹ 1.20 Cr"."""
    if value is None:
        return "—"
    v = Decimal(value)
    if v >= 100:
        return f"₹ {v / Decimal(100):.2f} Cr"
    if v >= 1:
        # Drop trailing .00 for whole-lakh values.
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return f"₹ {s} L"
    return f"₹ {v} L"


from django.contrib import admin as _django_admin  # noqa: E402  (avoid shadowing)


@_django_admin.register(Project)
class ProjectAdmin(SimpleHistoryAdmin, ImportExportModelAdmin, ModelAdmin):
    """Admin for property listings. Combines:

    - Unfold theme (visual)
    - django-import-export (CSV/XLSX import + export)
    - django-simple-history (per-row History tab)
    """

    resource_class = ProjectResource
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "thumbnail_tag", "title_with_link",
        "locality_with_city", "category", "developer",
        "status", "price_indian", "is_featured", "is_published",
        "published_at",
    )
    list_display_links = None  # title_with_link handles linking
    list_filter = ("is_published", "is_featured", "status", "category", "city")
    list_editable = ("is_featured",)
    list_per_page = 25
    list_select_related = ("category", "city", "developer")
    date_hierarchy = "created_at"
    search_fields = ("title", "slug", "locality", "developer__name")
    autocomplete_fields = ("category", "city", "developer")
    filter_horizontal = ("amenities",)
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "cover_preview")
    save_on_top = True
    inlines = (
        ProjectStatInline, ProjectHighlightInline,
        ProjectImageInline, FloorPlanInline,
    )
    fieldsets = (
        (None, {"fields": ("title", "slug", "tagline", "cover_image", "cover_preview")}),
        ("Classification", {
            "fields": ("category", "city", "locality", "developer", "status", "property_type"),
        }),
        ("Pricing & size", {
            "fields": ("price_starting_lacs", "price_display", "size_display"),
        }),
        ("Detail content", {"fields": ("description", "amenities", "rera_number", "map_embed_url")}),
        ("Publishing", {"fields": ("is_featured", "featured_order", "is_published", "published_at")}),
        ("Audit", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    actions = (
        "publish_selected", "unpublish_selected",
        "feature_selected", "unfeature_selected",
        "duplicate_listing",
    )

    # ---- Display callables ------------------------------------------------

    @unfold_display(description="")
    def thumbnail_tag(self, obj):
        if not obj.cover_image:
            return format_html(
                '<div style="width:60px;height:45px;background:#eee;'
                'border-radius:4px;display:flex;align-items:center;'
                'justify-content:center;color:#999;font-size:10px;">no img</div>',
            )
        try:
            url = obj.cover_thumbnail.url
        except Exception:
            url = obj.cover_image.url
        return format_html(
            '<img src="{}" style="width:60px;height:45px;'
            'object-fit:cover;border-radius:4px"/>',
            url,
        )

    @unfold_display(description="Title", ordering="title")
    def title_with_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:projects_project_change", args=[obj.pk]),
            obj.title,
        )

    @unfold_display(description="Location", ordering="city__name")
    def locality_with_city(self, obj):
        if obj.locality and obj.city_id:
            return f"{obj.locality}, {obj.city.name}"
        return obj.city.name if obj.city_id else "—"

    @unfold_display(description="Price", ordering="price_starting_lacs")
    def price_indian(self, obj):
        # Prefer the human-formatted price_display if admin set one;
        # otherwise compute Indian formatting from the decimal lakhs.
        if obj.price_display:
            return obj.price_display
        return _format_indian_price_lacs(obj.price_starting_lacs)

    @_django_admin.display(description="Cover preview")
    def cover_preview(self, obj):
        if not obj.cover_image:
            return "—"
        try:
            url = obj.cover_medium.url
        except Exception:
            url = obj.cover_image.url
        return format_html('<img src="{}" style="max-height:200px;border-radius:6px"/>', url)

    # ---- Custom actions ---------------------------------------------------

    @unfold_action(description="Publish selected")
    def publish_selected(self, request, queryset):
        updated = 0
        now = timezone.now()
        for p in queryset.filter(is_published=False):
            p.is_published = True
            if p.published_at is None:
                p.published_at = now
            p.save(update_fields=["is_published", "published_at"])
            updated += 1
        self.message_user(
            request, f"Published {updated} project(s).", level=messages.SUCCESS,
        )

    @unfold_action(description="Unpublish selected")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(
            request, f"Unpublished {updated} project(s).", level=messages.SUCCESS,
        )

    @unfold_action(description="Mark as featured")
    def feature_selected(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(
            request, f"Marked {updated} project(s) as featured.",
            level=messages.SUCCESS,
        )

    @unfold_action(description="Remove from featured")
    def unfeature_selected(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(
            request, f"Removed {updated} project(s) from featured.",
            level=messages.SUCCESS,
        )

    @unfold_action(description="Duplicate selected (creates drafts)")
    def duplicate_listing(self, request, queryset):
        created = 0
        for p in queryset:
            amenity_ids = list(p.amenities.values_list("id", flat=True))
            old_pk = p.pk
            p.pk = None
            p.id = None
            p.slug = ""  # let Project.save() re-slugify
            p.title = f"{p.title} (Copy)"
            p.is_published = False
            p.published_at = None
            p.is_featured = False
            p.cover_image = None
            p.save()
            if amenity_ids:
                p.amenities.set(amenity_ids)
            created += 1
        self.message_user(
            request, f"Duplicated {created} project(s) as drafts.",
            level=messages.SUCCESS,
        )

    # ---- Bulk image upload (carried over from step 4) --------------------

    def get_urls(self):
        return [
            path(
                "<int:project_id>/bulk-upload-images/",
                self.admin_site.admin_view(self.bulk_upload_images),
                name="projects_project_bulk_upload",
            ),
        ] + super().get_urls()

    def bulk_upload_images(self, request, project_id):
        project = self.get_object(request, project_id)
        if project is None:
            self.message_user(request, "Project not found.", level=messages.ERROR)
            return redirect("admin:projects_project_changelist")

        if request.method == "POST":
            form = BulkImageUploadForm(request.POST, request.FILES)
            files = request.FILES.getlist("images")
            if form.is_valid() and files:
                next_order = (project.images.count() or 0) + 1
                created = 0
                for f in files:
                    try:
                        img = ProjectImage(
                            project=project, image=f, display_order=next_order,
                        )
                        img.full_clean()
                        img.save()
                        next_order += 1
                        created += 1
                    except Exception as exc:
                        self.message_user(
                            request, f"{f.name}: {exc}", level=messages.WARNING,
                        )
                self.message_user(
                    request, f"Uploaded {created} image(s) to {project}.",
                    level=messages.SUCCESS,
                )
                return redirect(
                    reverse("admin:projects_project_change", args=[project_id]),
                )
        else:
            form = BulkImageUploadForm()

        return render(request, "admin/projects/bulk_upload.html", {
            "title": f"Bulk upload images — {project}",
            "form": form,
            "project": project,
            "opts": self.model._meta,
        })

    # ---- Change-form extras: bulk-upload + view-on-site + recent enquiries

    change_form_template = "admin/projects/project_change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["bulk_upload_url"] = reverse(
            "admin:projects_project_bulk_upload", args=[object_id],
        )

        try:
            project = Project.objects.get(pk=object_id)
            if project.is_published:
                extra_context["view_on_site_url"] = f"/api/v1/projects/{project.slug}/"
            extra_context["recent_enquiries"] = list(
                project.enquiries.order_by("-created_at")[:5],
            )
        except Project.DoesNotExist:
            pass

        return super().change_view(request, object_id, form_url, extra_context)
