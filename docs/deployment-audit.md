# Deployment Audit — Step 10

Pre-flight audit for the **single-droplet** DigitalOcean deployment
(`anjaneyaglobalrealty.com`, droplet `cspaces`, user `jarvis`).
Self-hosted Postgres + Redis, local-filesystem media, nginx + gunicorn.
No Docker, no managed services, no object storage.

Companion to [`deployment-runbook.md`](./deployment-runbook.md),
[`dns-setup.md`](./dns-setup.md).

## 1. Ubuntu version assumption

`provision.sh` is written for **Ubuntu 24.04 LTS** (installs
`python3.12`). It auto-detects the OS version and adapts:

- **24.04** → `python3.12` (the intended target)
- **22.04** → `python3.10`
- **20.04** → `python3.8` — *and you should plan an OS upgrade:* Ubuntu
  20.04 LTS reached end of standard support in April 2025.
- Anything else → the script aborts with an "Unsupported Ubuntu
  version" error rather than guessing.

**Confirm the droplet's version before running provisioning:**
`cat /etc/os-release | grep VERSION_ID`. If it's not 24.04, the script
still works, but double-check the chosen Python is acceptable.

## 2. `check --deploy` against production settings

Run with the env vars the prod module requires (the real values live in
`/home/jarvis/anjaneya/.env` on the droplet; here they're dummies):

```
CSRF_TRUSTED_ORIGINS=… ALLOWED_HOSTS=… CORS_ALLOWED_ORIGINS=… \
DB_PASSWORD=dummy LOG_DIR=./logs \
python manage.py check --deploy --settings=core.settings.production

→ 18 issues, ALL cosmetic:
  - 17× drf_spectacular.W001  — SerializerMethodField image-URL callables
    lack return type hints; the OpenAPI schema types them as "string"
    instead of "uri". Pre-existing since step 4. Not a deploy concern.
  - 1×  drf_spectacular        — operationId collision between
    /api/v1/projects/{id}/ and /api/v1/projects/{slug}/ — drf-spectacular
    auto-resolves with a numeral suffix. Cosmetic.
```

**Zero `security.W*` warnings.** `production.py` sets the full hardening
set: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`, HSTS (1 year, includeSubDomains, preload),
`SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`,
`X_FRAME_OPTIONS=DENY`, `SECURE_PROXY_SSL_HEADER`. `SECRET_KEY` has no
default — the process refuses to start without it.

The 18 cosmetic warnings are out of scope for a deployment step
(optional fix: `@extend_schema_field` on the four image-URL methods).

## 3. requirements split — confirmed

| File | Contents |
| --- | --- |
| `requirements.txt` | Production deps only, pinned. **Removed** per brief: `django-storages`, `boto3`, `dj-database-url` (+ their transitives `botocore`, `s3transfer`, `jmespath`) — uninstalled from the venv too. **Kept/added:** `django-redis`, `sentry-sdk`, `psycopg2-binary`. Celery + `django-celery-*` stay because the app code imports them. |
| `requirements-dev.txt` | `-r requirements.txt` plus dev/test tooling. The packages actually installed in the venv are pinned (`django-debug-toolbar`, `playwright` + deps, `python-magic-bin`, `flower` + deps). The brief's requested test/lint suite (`pytest*`, `ruff`, `mypy`, `bandit`, `factory-boy`, …) is listed unpinned — see deviation D-3. |

`python-magic-bin` is **dev-only** (Windows libmagic shim). On the Linux
droplet, `requirements.txt`'s `python-magic` resolves libmagic via the
apt `libmagic1` package that `provision.sh` installs.

## 4. localhost / DEBUG-only assumptions — clean

Audited `apps/` + `core/` for prod-unsafe assumptions:

- `localhost` / `127.0.0.1` references are confined to `base.py`
  *defaults* (overridden in prod) and `development.py` — no leakage
  into production behaviour.
- `console.EmailBackend` is only in `development.py`. `production.py`
  uses `smtp.EmailBackend`.
- No hardcoded `DEBUG=True` outside `development.py`.
- `core/urls.py`'s `if settings.DEBUG:` block (media serving +
  debug-toolbar URLs) is correctly skipped in production.
- `.env` (real, gitignored) holds local-dev values; `.env.example`
  (committed) is the 3-line local template; `.env.production.example`
  (committed) is the prod reference.

## 5. Celery decision — Option B (gunicorn-only)

Step 7 built a Celery + Redis async-email pipeline. The Step 10 brief
states "Step 7 was skipped — no worker/beat services." That premise is
factually wrong for this project, so the user was asked and chose
**Option B: follow the brief literally** — gunicorn-only systemd units,
no worker, no beat.

### ⚠️ KNOWN PRODUCTION LIMITATION

With Option B the async-email pipeline is **inert in production:**

- Enquiry POSTs succeed and save the row.
- `send_email_task.delay()` pushes a message into Redis and returns —
  no crash.
- **No worker consumes the queue** → enquiry-notification emails to
  `ENQUIRY_NOTIFICATION_EMAILS` are **never sent**, and the periodic
  digest tasks **never run**.

The site is otherwise fully functional. Admins track new enquiries via
`/admin/enquiries/enquiry/` (the dashboard "Unread enquiries" card +
the `status=new` filter). This is documented again, prominently, in
[`deployment-runbook.md`](./deployment-runbook.md) under "Known
limitation", and in `production.py`'s closing comment.

To enable async email later: add `celery -A core worker` (+ optionally
`beat`) systemd units modelled on `anjaneya.service`. No code changes.

`django-celery-beat` / `django-celery-results` stay in `INSTALLED_APPS`
— removing them would mean a migration to drop tables. Under Option B
they're dormant.

## 6. Deviations from the brief (faithful adaptations, applied without a separate ask)

None are architectural — each one matches the brief's *intent* to this
project's actual state. Listed for the record.

| # | Brief said | Adapted to | Why |
| - | --- | --- | --- |
| D-1 | `STATICFILES_STORAGE = …` + `DEFAULT_FILE_STORAGE = …` (legacy names) in `production.py` / `development.py` | The `STORAGES` dict | `base.py` already defines `STORAGES`; Django 5.2 raises `ImproperlyConfigured` if the legacy names coexist with it. Same backends, correct syntax. |
| D-2 | `production.py` `LOGGING` hardcodes `/var/log/anjaneya/…` | `LOG_DIR = config("LOG_DIR", default="/var/log/anjaneya")` + `delay=True` on the file handlers | `RotatingFileHandler` opens its file at construction. Hardcoding the path crashes `check --deploy` on any machine without that dir (e.g. the Windows dev box). Default is unchanged; `delay=True` defers the open; the dir is overridable for local runs. |
| D-3 | `requirements-dev.txt` lists `pytest`, `ruff`, `bandit`, `mypy`, … ; `pre_deploy_check.sh` runs `pytest --cov` + `ruff` + `bandit -c pyproject.toml` | `pre_deploy_check.sh` runs `manage.py test` + `makemigrations --check` + `check --deploy`; the lint/security lines are present but commented | The project's test runner is Django's `manage.py test` (85 TestCase tests). There's no `pytest.ini` / `pyproject.toml` / ruff / bandit config. Wiring up a new test/lint toolchain is its own task, not a deployment step. The dev-requirements file still lists the tooling (unpinned) so it's there when someone does that work. |
| D-4 | nginx rate-limit `location ~ ^/api/v1/(contact\|properties/[^/]+/enquiries)/` | `location ~ ^/api/v1/enquiries/` | Those endpoints don't exist in this project. The real public-write endpoint is `/api/v1/enquiries/` (`apps/enquiries/urls.py`). |
| D-5 | `provision.sh` Ubuntu detection in the brief | kept as-is, plus an explicit "abort on unsupported version" branch | Brief's `case` already covered 24.04/22.04/20.04; the audit just makes the failure mode explicit (see §1). |
| D-6 | `base.py` ran `LOGS_DIR.mkdir()` with a non-`delay` file handler | added `delay=True` to base's file handler | Consistency with prod + makes `base.py` import-safe everywhere. The `logs/` dir creation in dev is harmless and intended. |

## 7. Production blockers

**None.** After the Phase B settings rewrite, `check --deploy` is clean
of security warnings, all required env vars are documented in
`.env.production.example`, and every deployment artifact is in the repo.

The one operational caveat — async email being inert (§5) — is a
**deliberate, documented** consequence of the chosen Celery option, not
a blocker. The site deploys and serves correctly.

## 8. Pre-deploy checklist (for whoever runs the deployment)

- [ ] Droplet is Ubuntu 24.04 (`cat /etc/os-release`); if not, see §1.
- [ ] DNS A records point at the droplet — [`dns-setup.md`](./dns-setup.md), verified with `dig`.
- [ ] `git clone` the repo to `/home/jarvis/anjaneya`.
- [ ] `sudo bash deploy/scripts/provision.sh` — save the printed DB password.
- [ ] venv created, `pip install -r requirements.txt`.
- [ ] `.env` filled from `.env.production.example`, `chmod 600`.
- [ ] `media/` + `staticfiles/` dirs created.
- [ ] `migrate`, `collectstatic`, `createsuperuser`.
- [ ] `install_services.sh`, `install_nginx.sh`, `certbot`.
- [ ] `curl https://anjaneyaglobalrealty.com/health/ready/` → `{"status":"ok"}`.
- [ ] `bash deploy/scripts/backup.sh` runs and writes to `/home/jarvis/backups/`.
- [ ] Note the async-email limitation (§5) — set expectations with whoever monitors enquiries.

Full step-by-step: [`deployment-runbook.md`](./deployment-runbook.md).
