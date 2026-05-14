"""Single chokepoint for outbound email.

All callers go through `send_templated_email`. No app should reach for
`django.core.mail.send_mail` directly — keeping construction here means
templates, from-address, multipart wiring, and logging are uniform.
"""

from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


log = logging.getLogger(__name__)


def _normalize_recipients(to: str | Iterable[str]) -> list[str]:
    if isinstance(to, str):
        return [a.strip() for a in to.split(",") if a.strip()]
    return [a.strip() for a in to if a and a.strip()]


def send_templated_email(
    *,
    subject: str,
    template_base: str,
    context: dict,
    to: str | Iterable[str],
    from_email: str | None = None,
) -> int:
    """Render `<template_base>.txt` + `.html`, build a multipart message, send.

    Returns the number of successfully delivered messages (Django's
    `EmailMessage.send()` return value). Raises on error so the Celery
    task layer can retry — callers should NOT catch here.
    """
    recipients = _normalize_recipients(to)
    if not recipients:
        log.info("send_templated_email skipped: no recipients (template=%s)", template_base)
        return 0

    text_body = render_to_string(f"{template_base}.txt", context)
    html_body = render_to_string(f"{template_base}.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    msg.attach_alternative(html_body, "text/html")
    return msg.send(fail_silently=False)
