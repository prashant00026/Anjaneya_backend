"""Deprecated shim.

Step 6's synchronous `send_enquiry_email` was replaced in step 7 by the
async Celery pipeline in `apps/notifications/tasks.py`. This file is
kept only so a stale import doesn't crash; new code should call
`notifications.tasks.queue_enquiry_notification(enquiry)` instead.
"""

from notifications.tasks import queue_enquiry_notification


def send_enquiry_email(enquiry):
    """Backwards-compatible wrapper. Queues the async task; returns None."""
    queue_enquiry_notification(enquiry)
