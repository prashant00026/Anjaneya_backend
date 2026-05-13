# Anjaneya Real Estate — Backend

Production-ready Django + DRF backend for the Anjaneya Real Estate platform.

## Stack

- **Python** 3.11+
- **Django** 5.x
- **Django REST Framework** + **SimpleJWT** (auth)
- **django-cors-headers**, **django-filter**
- **drf-spectacular** (OpenAPI / Swagger / ReDoc)
- **PostgreSQL** (prod) / **SQLite** (dev)
- **psycopg2-binary**, **python-decouple**, **Pillow**
- **django-storages** (future S3 media), **WhiteNoise** (static)
- **Gunicorn** (prod server)

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

## Notes

- `AUTH_USER_MODEL` is set to `accounts.User`. The `accounts` app will be
  created in step 2 of the bootstrap process; until then, migrations
  expecting that model will fail.
- `apps/` is on `sys.path`, so apps are imported as `from accounts...`
  rather than `from apps.accounts...`.
