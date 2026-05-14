# Notifications Spec — Step 7

Async email + periodic admin notifications via Celery + Redis.
Companion to [`backend-plan.md`](./backend-plan.md), [`features-spec.md`](./features-spec.md).

## 1. What step 7 ships

Before: step 6 used a synchronous `post_save` signal that called
`send_mail(fail_silently=True)` directly from the API thread.

After: every email goes through one Celery task with retry + backoff,
and terminal failures are recorded in a `FailedNotification` table.

## 2. Email types

Each template lives at `templates/emails/<base>.html` + `.txt`. They all
extend `templates/emails/base.html` for the chrome.

| Template base | Trigger | Recipients | Source |
| --- | --- | --- | --- |
| `emails/inquiry_property` | `Enquiry.save()` where `project` is set | `INQUIRY_NOTIFICATION_EMAILS` | `notifications.tasks.queue_inquiry_notification` |
| `emails/inquiry_contact` | `Enquiry.save()` where `project` is null | `INQUIRY_NOTIFICATION_EMAILS` | same |
| `emails/daily_summary` | beat: every day at 09:00 server time | `INQUIRY_NOTIFICATION_EMAILS` | `notifications.tasks.send_daily_admin_summary` |
| `emails/unread_reminder` | beat: every 6 hours | `INQUIRY_NOTIFICATION_EMAILS` | `notifications.tasks.remind_unread_inquiries` |

All four can also be queued ad-hoc from `/admin/notifications/failednotification/test-email/` for SMTP smoke testing.

## 3. Periodic tasks (beat)

Registered automatically via `post_migrate` in `apps/notifications/apps.py`
so a fresh install gets them on first migration. Visible/tunable in
admin at `/admin/django_celery_beat/`.

| Task | Schedule | Behaviour |
| --- | --- | --- |
| `notifications.tasks.send_daily_admin_summary` | daily, 09:00 (cron `0 9 * * *`) | Roll-up: site enquiries (24h), project enquiries (24h), top 5 projects by enquiry count, top 5 localities, new published projects. Skips quietly if `INQUIRY_NOTIFICATION_EMAILS` is empty. |
| `notifications.tasks.remind_unread_inquiries` | every 6 hours (cron `0 */6 * * *`) | Lists enquiries with `status=new` older than 24h (top 25). Nothing to send if everything's been touched. |

### Skipped (deferred from steps 5+6)

- `expire_featured_properties` — needs `Project.featured_until`; deferred in step 6.
- `refresh_search_vectors` — needs `Project.search_vector` + Postgres FTS; deferred in step 5.

Both can be added later by introducing the underlying fields first.

## 4. Task: `send_email_task`

```python
notifications.tasks.send_email_task.delay(
    subject="...",
    template_base="emails/inquiry_property",
    context={...},
    to=["ops@example.com"],          # str or list
    from_email=None,                  # falls back to DEFAULT_FROM_EMAIL
)
```

- **Retry policy:** `autoretry_for = (SMTPException, ConnectionError, OSError, TimeoutError)`. Exponential backoff starting at 60s, capped at 600s, jittered. `max_retries=5`.
- **Terminal failure:** Celery invokes `EmailTask.on_failure`, which persists subject + recipients + template + context + error message to `FailedNotification`. Admin can retry from `/admin/notifications/failednotification/`.
- **Body:** lazily imports + calls `notifications.services.send_templated_email(...)`. Single chokepoint — no other app should construct emails directly.

## 5. `FailedNotification` model

| Field | Type | Notes |
| --- | --- | --- |
| `subject` | CharField(255) | |
| `template_base` | CharField(120) | e.g. `emails/inquiry_property` |
| `recipients` | TextField | comma-separated |
| `context_json` | JSONField | full context passed to the task; sufficient to retry |
| `from_email` | CharField(255) | empty = use `DEFAULT_FROM_EMAIL` on retry |
| `error_message` | TextField | `"<ExceptionClass>: <msg>"` |
| `last_retried_at` | DateTimeField, null | stamped by the "Retry" admin action |
| `created_at` | DateTimeField | |

## 6. Running locally

This step adds **two new background services**. Redis is required to
actually run a worker; on Windows install [Memurai](https://www.memurai.com/) or run Redis via WSL/Docker.

```powershell
# Terminal 1 — Django (already configured)
.\venv\Scripts\python.exe manage.py runserver

# Terminal 2 — Redis
#   Windows: memurai (default port 6379)
#   macOS:   brew services start redis
#   Linux:   sudo service redis-server start

# Terminal 3 — Celery worker
.\venv\Scripts\celery.exe -A core worker -l info --pool=solo

# Terminal 4 — Celery beat (only when you want periodic tasks to fire)
.\venv\Scripts\celery.exe -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Terminal 5 — Flower (optional, monitoring UI at http://localhost:5555/)
.\venv\Scripts\celery.exe -A core flower --port=5555
```

> **Windows note:** `--pool=solo` avoids the fork-on-Windows breakage
> with the default prefork pool. Linux/macOS workers don't need it.

### Without Redis

Tests use `CELERY_TASK_ALWAYS_EAGER=True` so they execute tasks inline
and don't need a broker. The API also keeps working without a worker —
`send_email_task.delay(...)` just queues into Redis and returns; if no
worker drains the queue, emails simply pile up. Inquiry creation does
not block on Redis availability beyond the network round-trip.

## 7. Settings (`core/settings/base.py`)

| Key | Default | Env var |
| --- | --- | --- |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | `CELERY_BROKER_URL` |
| `CELERY_RESULT_BACKEND` | `django-db` | — |
| `CELERY_BEAT_SCHEDULER` | `django_celery_beat.schedulers:DatabaseScheduler` | — |
| `CELERY_TASK_TIME_LIMIT` | 5 min hard | — |
| `CELERY_TASK_SOFT_TIME_LIMIT` | 4 min soft | — |
| `CELERY_TASK_ACKS_LATE` | `True` — re-queue if worker dies | — |
| `CELERY_TASK_REJECT_ON_WORKER_LOST` | `True` | — |
| `CELERY_WORKER_PREFETCH_MULTIPLIER` | `1` | — |
| `CELERY_TIMEZONE` | `Asia/Kolkata` (= `TIME_ZONE`) | — |
| `EMAIL_BACKEND` | console in dev, SMTP in prod | `EMAIL_BACKEND` |
| `DEFAULT_FROM_EMAIL` | `Anjaneya <no-reply@...>` | `DEFAULT_FROM_EMAIL` |
| `INQUIRY_NOTIFICATION_EMAILS` | empty (no-op) | `INQUIRY_NOTIFICATION_EMAILS` (CSV) |

Standard SMTP knobs (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`) ride on Django's defaults.

## 8. Transaction safety

Every API path that creates a model + queues an email wraps the call
in `transaction.on_commit(...)`. Without this the worker could pick up
the task before the DB row has committed and see a phantom `DoesNotExist`.
The wiring lives in `apps/enquiries/apps.py`:

```python
post_save.connect(
    lambda sender, instance, created, **kw: created and transaction.on_commit(
        lambda: queue_inquiry_notification(instance)
    ),
    sender=Enquiry,
)
```

Test code that needs to assert on `mail.outbox` wraps the test body in
`self.captureOnCommitCallbacks(execute=True)` — APITestCase wraps in a
transaction that rolls back, so `on_commit` callbacks would otherwise
never fire.

## 9. Admin tools

- `/admin/notifications/failednotification/` — list of failed sends. Each row stores enough context to re-fire the task via the "Retry selected" bulk action.
- `/admin/notifications/failednotification/test-email/` — small form (recipient + template) that queues a task with sample context. Useful for verifying SMTP creds without faking an inquiry. Staff only.
- `/admin/django_celery_beat/periodictask/` — edit cron expressions / disable a schedule live.
- `/admin/django_celery_results/taskresult/` — every task's outcome, status, traceback if any.

## 10. Tests

`apps/notifications/tests.py` — 9 tests. `apps/enquiries/tests_step6.py`
was updated to use `captureOnCommitCallbacks` since email is now async.

Notable design notes encoded in the tests:
- `EmailTask.on_failure` is tested directly rather than by exhausting the retry budget. Eager-mode retries don't loop and would just propagate Celery's `Retry` exception; the retry logic itself is Celery's well-trodden code. What we own is the persistence in `on_failure`.
- The signal test uses `mock.patch(...)` to confirm `queue_inquiry_notification` runs from inside an `on_commit` callback rather than synchronously.

## 11. Deferred / future

- Move `send_inquiry_email` consumers (currently just one — the Enquiry signal) onto a higher-level helper if more apps start producing emails.
- Add an admin dashboard widget for "Tasks in last 24h" using `django-celery-results` — skipped for now per the brief's "don't over-build" note.
- Slack / SMS / push notifications — not in scope until there's a product request.
- A proper unsubscribe flow — only relevant once we email external users (today every recipient is admin staff via env-configured CSV).
