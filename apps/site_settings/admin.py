from django.contrib import admin as django_admin
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin

from .models import CmsPage, SiteSettings


@django_admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    list_display = ("phone", "email", "copyright_year")
    fieldsets = (
        ("Contact", {"fields": ("phone", "email", "address")}),
        ("Social", {
            "fields": (
                "whatsapp_url", "instagram_url", "linkedin_url",
                "facebook_url", "youtube_url",
            ),
        }),
        ("Homepage hero stats", {
            "fields": (
                "hero_stat_clients", "hero_stat_clients_label",
                "hero_stat_value", "hero_stat_value_label",
            ),
        }),
        ("Footer", {"fields": ("copyright_year",)}),
    )

    # Singleton: route the changelist directly to the only edit page.
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse("admin:site_settings_sitesettings_change", args=[obj.pk]))


@django_admin.register(CmsPage)
class CmsPageAdmin(ModelAdmin):
    list_display = ("slug", "title", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("slug", "title", "body")
    prepopulated_fields = {"slug": ("title",)}
