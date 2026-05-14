# Import the Celery app at package load so `@shared_task` decorators
# register against it and `celery -A core ...` resolves correctly.
from .celery import app as celery_app

__all__ = ("celery_app",)
