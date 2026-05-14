from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects"

    def ready(self):
        from django.db.models.signals import post_delete

        from common.signals import delete_file_fields

        from .models import FloorPlan, Project, ProjectImage

        for model in (Project, ProjectImage, FloorPlan):
            post_delete.connect(
                lambda sender, instance, **kw: delete_file_fields(instance),
                sender=model,
                weak=False,
                dispatch_uid=f"clean_files_{model._meta.label_lower}",
            )
