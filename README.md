# Anjaneya Real Estate — Backend

Production-ready Django + DRF backend for the Anjaneya Real Estate platform.

## Stack

- **Python** 3.11+
- **Django** 5.x
- **Django REST Framework** + **SimpleJWT** (auth)
- **django-cors-headers**, **django-filter**
- **drf-spectacular** (OpenAPI / Swagger / ReDoc)
- **PostgreSQL** (prod, on the droplet) / **SQLite** (dev)
- **psycopg2-binary**, **python-decouple**, **Pillow**
- **WhiteNoise** (static), **Gunicorn** (prod server), **nginx** (reverse proxy + TLS)
- **Redis** (prod cache, on the droplet)
- **Celery + django-celery-beat/results** (async email — code present; no worker runs in the current deployment, see Deployment below)
- **django-imagekit** (thumbnails), **python-magic** (real mime sniff)
- **django-unfold** (admin theme), **django-import-export**, **django-simple-history**

## Quick start

```bash
# 1. Clone
git clone <repo-url> Anjaneya
cd Anjaneya

# 2. Virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# then edit .env and set SECRET_KEY, DB_*, CORS_ALLOWED_ORIGINS, etc.

# 5. Migrate + run
python manage.py migrate
python manage.py runserver
```

## Running locally with Celery

The web process works fine on its own — enquiry emails queue into Redis
and drain when a worker is online. To actually deliver them (and run
the periodic admin tasks) you need three more processes:

```powershell
# Terminal 1 — Django (above)

# Terminal 2 — Redis
#   Windows: install Memurai (https://www.memurai.com/) — runs on 6379
#   macOS:   brew services start redis
#   Linux:   sudo service redis-server start

# Terminal 3 — Celery worker
#   On Windows the prefork pool is broken; `--pool=solo` is required.
.\venv\Scripts\celery.exe -A core worker -l info --pool=solo

# Terminal 4 — Celery beat (only when testing periodic schedules)
.\venv\Scripts\celery.exe -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Optional — Flower monitoring UI at http://localhost:5555/
.\venv\Scripts\celery.exe -A core flower --port=5555
```

The API will be live at <http://127.0.0.1:8000/>.

## API endpoints

| Path             | Purpose                       |
| ---------------- | ----------------------------- |
| `/admin/`        | Django admin                  |
| `/api/v1/`       | Versioned API root            |
| `/api/schema/`   | OpenAPI 3 schema (JSON)       |
| `/api/docs/`     | Swagger UI                    |
| `/api/redoc/`    | ReDoc UI                      |

## Settings

Settings are split into a package at `core/settings/`:

- `base.py`         — shared settings
- `development.py`  — `DEBUG=True`, SQLite (default for `manage.py`)
- `production.py`   — `DEBUG=False`, Postgres, HSTS / SSL hardening

Switch environments via `DJANGO_SETTINGS_MODULE`:

```bash
# Production
export DJANGO_SETTINGS_MODULE=core.settings.production
```

## Folder structure

```
Anjaneya/
├── apps/             # All Django apps live here (importable as `from <app>...`)
├── core/             # Project package
│   ├── settings/     # base / development / production
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── media/            # User-uploaded files (dev)
├── static/           # Source static assets
├── staticfiles/      # `collectstatic` target
├── templates/        # Shared templates
├── logs/             # Rotating log output
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Deployment

Production runs on a single DigitalOcean droplet (`cspaces`, BLR1):
nginx → gunicorn (Unix socket) → Django, with PostgreSQL, Redis, and
local-filesystem media all on the same machine. No Docker, no managed
services, no object storage.

All deployment artifacts live in `deploy/`:

```
deploy/
├── gunicorn.conf.py            # 5 gthread workers × 2 threads (4 GB / 2 vCPU)
├── systemd/
│   ├── anjaneya.service        # gunicorn unit
│   └── anjaneya.socket         # Unix socket unit
├── nginx/anjaneya.conf         # reverse proxy + TLS + /static/ + /media/
└── scripts/
    ├── provision.sh            # one-time droplet setup (Postgres/Redis/nginx/...)
    ├── install_services.sh     # install the systemd units
    ├── install_nginx.sh        # install the nginx site
    ├── deploy.sh               # ongoing deploys (pull → migrate → reload → health)
    ├── backup.sh               # nightly DB dump + media tarball (cron)
    ├── restore_db.sh           # restore the DB from a backup
    └── pre_deploy_check.sh     # local pre-push sanity checks
```

**Full step-by-step instructions: [`docs/deployment-runbook.md`](docs/deployment-runbook.md).**
Supporting docs: [`deployment-audit.md`](docs/deployment-audit.md),
[`dns-setup.md`](docs/dns-setup.md).

> **Known limitation:** the deployment runs gunicorn only — no Celery
> worker. The app's async-email code queues into Redis but nothing
> consumes it, so enquiry-notification emails are not sent in
> production. Admins track new enquiries via `/admin/`. See the
> runbook's "Known limitation" section to enable async email later.

## Notes

- No custom user model — Django's built-in `auth.User` handles `/admin/`
  login. This is a listing-only site with no public signup.
- `apps/` is on `sys.path`, so apps are imported as `from projects...`
  rather than `from apps.projects...`.
- Local dev uses SQLite + LocMem cache + console email — no env vars
  needed beyond an optional `SECRET_KEY`. Production uses Postgres +
  Redis + SMTP, all configured via `/home/jarvis/anjaneya/.env`.
