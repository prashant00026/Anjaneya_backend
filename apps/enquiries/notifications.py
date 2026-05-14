"""Deprecated shim.

Step 6's synchronous `send_inquiry_email` was replaced in step 7 by the
async Celery pipeline in `apps/notifications/tasks.py`. This file is
kept only so a stale import doesn't crash; new code should call
`notifications.tasks.queue_inquiry_notification(enquiry)` instead.
"""

from notifications.tasks import queue_inquiry_notification


def send_inquiry_email(enquiry):
    """Backwards-compatible wrapper. Queues the async task; returns None."""
    queue_inquiry_notification(enquiry)
