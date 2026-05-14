"""Celery application for the Anjaneya backend.

Settings are pulled from Django (`CELERY_*` keys in `core/settings/...`).
Tasks live under each app's `tasks.py` and are auto-discovered.
"""

from __future__ import annotations

import logging
import os

from celery import Celery
from celery.signals import task_failure


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")

app = Celery("core")

# All Celery configuration is taken from Django settings, namespaced
# CELERY_*  (e.g. CELERY_BROKER_URL → broker_url).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover @shared_task definitions in every INSTALLED_APP.
app.autodiscover_tasks()


_log = logging.getLogger(__name__)


@task_failure.connect
def _log_task_failure(sender=None, task_id=None, exception=None, traceback=None, **kwargs):
    """Persist task failures to the log even if no FailedNotification row gets written."""
    _log.error(
        "Celery task failed: task=%s id=%s exc=%r",
        getattr(sender, "name", sender), task_id, exception,
    )
