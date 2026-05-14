from django.apps import AppConfig


class EnquiriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "enquiries"

    def ready(self):
        from django.db import transaction
        from django.db.models.signals import post_save

        from .models import Enquiry

        def _on_create(sender, instance, created, **kwargs):
            if not created:
                return
            # Defer until after the surrounding transaction commits so the
            # worker is guaranteed to see the row when it picks the task up.
            # `on_commit` runs the callback immediately if no transaction
            # is active, so admin shell creation works too.
            from notifications.tasks import queue_inquiry_notification

            transaction.on_commit(lambda: queue_inquiry_notification(instance))

        post_save.connect(
            _on_create, sender=Enquiry, weak=False,
            dispatch_uid="enquiries_send_notification_on_create",
        )
