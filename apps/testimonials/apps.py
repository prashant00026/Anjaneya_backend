from django.apps import AppConfig


class TestimonialsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "testimonials"

    def ready(self):
        from django.db.models.signals import post_delete

        from common.signals import delete_file_fields

        from .models import Testimonial

        post_delete.connect(
            lambda sender, instance, **kw: delete_file_fields(instance),
            sender=Testimonial, weak=False, dispatch_uid="clean_files_testimonials_testimonial",
        )
