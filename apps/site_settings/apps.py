from django.apps import AppConfig


class SiteSettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "site_settings"

    def ready(self):
        from django.db.models.signals import post_delete

        from common.signals import delete_file_fields

        from .models import CmsPage

        post_delete.connect(
            lambda sender, instance, **kw: delete_file_fields(instance),
            sender=CmsPage, weak=False, dispatch_uid="clean_files_site_settings_cmspage",
        )
