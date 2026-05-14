"""
Development settings — local work only.

SQLite, LocMem cache, console email. No env vars needed for basic
local dev: every value below has a safe default.
"""

import sys

from decouple import config

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE

DEBUG = True

SECRET_KEY = config("SECRET_KEY", default="dev-insecure-secret-key-do-not-use-in-prod")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# SQLite — file-based, gitignored. Production uses managed Postgres.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# In-process cache — no Redis dependency for local dev.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "anjaneya-dev",
    }
}

# Mail to stdout — we never accidentally email real people in dev.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Permissive CORS for a local frontend dev server.
CORS_ALLOW_ALL_ORIGINS = True

# Storage: filesystem media + plain staticfiles backend.
# base.py defaults `staticfiles` to WhiteNoise's manifest storage,
# which needs `collectstatic` to resolve hashed names — not run in
# dev / tests, so we swap to the simple backend here. Django 5.2
# requires the `STORAGES` dict, not the legacy STATICFILES_STORAGE /
# DEFAULT_FILE_STORAGE names.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


# ---------------------------------------------------------------------------
# django-debug-toolbar — query counts / panels in dev only.
# Visit /__debug__/ or any page with DEBUG=True; the toolbar is limited
# to INTERNAL_IPS so it won't render for external clients.
# ---------------------------------------------------------------------------
INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]

# Insert as early as possible so it wraps every other middleware.
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    *MIDDLEWARE,
]

INTERNAL_IPS = ["127.0.0.1", "::1"]

# Disable the toolbar entirely during test runs (it pollutes
# assertNumQueries and trips its own E001 check when Django flips
# DEBUG=False for tests).
if "test" in sys.argv:
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda r: False,
        "IS_RUNNING_TESTS": False,
    }
