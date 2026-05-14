from django.apps import AppConfig


class TeamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "team"

    def ready(self):
        from django.db.models.signals import post_delete

        from common.signals import delete_file_fields

        from .models import TeamMember

        post_delete.connect(
            lambda sender, instance, **kw: delete_file_fields(instance),
            sender=TeamMember, weak=False, dispatch_uid="clean_files_team_teammember",
        )
