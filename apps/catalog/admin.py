from django.contrib import admin as django_admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from unfold.decorators import display as unfold_display

from .models import Amenity, Category, City, Developer


# ---------------------------------------------------------------------------
# import-export resources
# ---------------------------------------------------------------------------

class CityResource(resources.ModelResource):
    class Meta:
        model = City
        import_id_fields = ("slug",)
        fields = ("id", "slug", "name", "display_order", "is_active")
        export_order = fields


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        import_id_fields = ("slug",)
        fields = ("id", "slug", "name", "description", "display_order", "is_active")
        export_order = fields


class DeveloperResource(resources.ModelResource):
    class Meta:
        model = Developer
        import_id_fields = ("slug",)
        fields = ("id", "slug", "name", "description", "website",
                  "display_order", "is_active")
        export_order = fields


class AmenityResource(resources.ModelResource):
    class Meta:
        model = Amenity
        import_id_fields = ("slug",)
        fields = ("id", "slug", "name", "display_order", "is_active")
        export_order = fields


# ---------------------------------------------------------------------------
# Admins
# ---------------------------------------------------------------------------

class _NamedAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("name", "slug", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    import_form_class = ImportForm
    export_form_class = ExportForm


@django_admin.register(City)
class CityAdmin(_NamedAdmin):
    resource_class = CityResource


@django_admin.register(Category)
class CategoryAdmin(_NamedAdmin):
    resource_class = CategoryResource


@django_admin.register(Developer)
class DeveloperAdmin(_NamedAdmin):
    resource_class = DeveloperResource
    list_display = (
        "logo_tag", "name", "slug", "website", "display_order", "is_active",
    )

    @unfold_display(description="")
    def logo_tag(self, obj):
        if not obj.logo:
            return "—"
        return format_html(
            '<img src="{}" style="height:32px;width:auto;border-radius:4px"/>',
            obj.logo.url,
        )


@django_admin.register(Amenity)
class AmenityAdmin(_NamedAdmin):
    resource_class = AmenityResource
    list_display = ("icon_tag", "name", "slug", "display_order", "is_active")

    @unfold_display(description="")
    def icon_tag(self, obj):
        if not obj.icon:
            return "—"
        return format_html(
            '<img src="{}" style="height:24px;width:24px;object-fit:contain"/>',
            obj.icon.url,
        )
