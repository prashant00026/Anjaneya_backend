from django.contrib import admin as django_admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display as unfold_display

from .models import TeamMember


@django_admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = ("photo_tag", "name", "designation", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "designation")
    prepopulated_fields = {"slug": ("name",)}

    @unfold_display(description="")
    def photo_tag(self, obj):
        if not obj.photo:
            return "—"
        return format_html(
            '<img src="{}" style="height:40px;width:40px;'
            'object-fit:cover;border-radius:50%"/>',
            obj.photo.url,
        )
