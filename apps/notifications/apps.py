from django.apps import AppConfig
from django.db.models.signals import post_migrate


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
        # Register beat schedules after migrations so a fresh install gets
        # them without a manual fixture load. Only fire when our own app's
        # migrations run (the signal fires once per app).
        post_migrate.connect(_register_beat_schedule, sender=self)


def _register_beat_schedule(sender, **kwargs):
    """Idempotently create the two periodic-task rows.

    `django_celery_beat`'s tables come from a third-party app, so we
    can't depend on them at import time — only after `post_migrate`.
    """
    try:
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
    except ImportError:
        return

    daily_9am, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="9", day_of_week="*",
        day_of_month="*", month_of_year="*",
    )
    PeriodicTask.objects.update_or_create(
        name="notifications.daily_admin_summary",
        defaults={
            "task": "notifications.tasks.send_daily_admin_summary",
            "crontab": daily_9am,
            "enabled": True,
            "description": "Roll-up of new enquiries + projects each morning.",
        },
    )

    every_6h, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="*/6", day_of_week="*",
        day_of_month="*", month_of_year="*",
    )
    PeriodicTask.objects.update_or_create(
        name="notifications.remind_unread_inquiries",
        defaults={
            "task": "notifications.tasks.remind_unread_inquiries",
            "crontab": every_6h,
            "enabled": True,
            "description": "Nag email for inquiries still 'new' after 24 hours.",
        },
    )
