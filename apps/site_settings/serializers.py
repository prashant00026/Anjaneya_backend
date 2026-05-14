from rest_framework import serializers

from .models import CmsPage, SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = (
            "phone", "email", "address",
            "whatsapp_url", "instagram_url", "linkedin_url",
            "facebook_url", "youtube_url",
            "hero_stat_clients", "hero_stat_clients_label",
            "hero_stat_value", "hero_stat_value_label",
            "copyright_year",
        )


class CmsPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CmsPage
        fields = ("slug", "title", "body", "hero_image", "updated_at")
