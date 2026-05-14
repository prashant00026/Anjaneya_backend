"""
Development settings.

Used for local work. DEBUG is on, SQLite is the default database,
and CORS is permissive so a local frontend dev server can connect.
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE

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

# Send mail to stdout in dev so we never accidentally email real people.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# WhiteNoise's manifest backend (base.py default) needs collectstatic to
# resolve hashed filenames. In dev / tests we serve files directly, so
# swap to the simple backend.
from .base import STORAGES as _STORAGES  # noqa: E402

STORAGES = {
    **_STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# ---------------------------------------------------------------------------
# django-debug-toolbar — query counts / panels in dev only.
# Visit /__debug__/ or just any page with DEBUG=True; the toolbar is
# limited to INTERNAL_IPS so it won't render for external clients.
# ---------------------------------------------------------------------------
INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]

# Insert as early as possible so it can wrap every other middleware.
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    *MIDDLEWARE,
]

INTERNAL_IPS = ["127.0.0.1", "::1"]

# Skip the toolbar entirely during test runs (it pollutes assertNumQueries
# and trips its own E001 check when Django flips DEBUG=False for tests).
import sys  # noqa: E402

if "test" in sys.argv:
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda r: False,
        "IS_RUNNING_TESTS": False,
    }
