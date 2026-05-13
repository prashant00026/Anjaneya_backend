"""
Development settings.

Used for local work. DEBUG is on, SQLite is the default database,
and CORS is permissive so a local frontend dev server can connect.
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = True

ALLOWED_HOSTS = ["*"]

# SQLite fallback for local development. Switch to Postgres in production
# (or by pointing DATABASE_URL at a Postgres instance).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Be permissive in dev — the frontend dev server URL is set via .env in prod.
CORS_ALLOW_ALL_ORIGINS = True
