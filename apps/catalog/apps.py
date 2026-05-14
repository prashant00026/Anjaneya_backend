from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"

    def ready(self):
        from django.db.models.signals import post_delete

        from common.signals import delete_file_fields

        from .models import Amenity, Developer

        for model in (Amenity, Developer):
            post_delete.connect(
                lambda sender, instance, **kw: delete_file_fields(instance),
                sender=model,
                weak=False,
                dispatch_uid=f"clean_files_{model._meta.label_lower}",
            )
