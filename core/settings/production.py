"""
Production settings — single DigitalOcean droplet (cspaces, BLR1).

Everything runs on one machine:
  - Database: PostgreSQL 16 installed on the droplet
  - Cache:    Redis installed on the droplet
  - Media:    local filesystem at BASE_DIR/media, served by nginx
  - Static:   collected to staticfiles/, served by nginx + WhiteNoise
  - Email:    SMTP

No managed services, no Spaces, no S3, no Docker.

Every value comes from the environment (`/home/jarvis/anjaneya/.env`,
mode 600). `SECRET_KEY` and `DB_PASSWORD` have no defaults — the
process refuses to start without them, which is what we want.
"""

from decouple import Csv, config

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = False

SECRET_KEY = config("SECRET_KEY")  # no default — must be set in .env
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())


# ---------------------------------------------------------------------------
# Database — PostgreSQL installed on the droplet
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="anjaneya"),
        "USER": config("DB_USER", default="anjaneya"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
    }
}


# ---------------------------------------------------------------------------
# Cache — Redis on the droplet
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "IGNORE_EXCEPTIONS": True,
        },
    }
}
DJANGO_REDIS_IGNORE_EXCEPTIONS = True


# ---------------------------------------------------------------------------
# Static & media — both on the droplet's local filesystem, served by nginx
# ---------------------------------------------------------------------------
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media: local filesystem on the droplet at /home/jarvis/anjaneya/media,
# served directly by nginx (see deploy/nginx/anjaneya.conf). NO Spaces,
# NO S3, NO django-storages — backups are handled by deploy/scripts/backup.sh
# plus DigitalOcean droplet snapshots.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Django 5.2 requires the STORAGES dict — the legacy STATICFILES_STORAGE /
# DEFAULT_FILE_STORAGE names cannot coexist with the STORAGES dict already
# defined in base.py. Same backends the brief intended, expressed correctly.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv())


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())
CORS_ALLOW_CREDENTIALS = False


# ---------------------------------------------------------------------------
# Email — SMTP
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default="Anjaneya Global Realty <no-reply@anjaneyaglobalrealty.com>",
)


# ---------------------------------------------------------------------------
# Logging — file-based (no Docker; the droplet keeps logs on disk)
#
# LOG_DIR defaults to /var/log/anjaneya (created by provision.sh). It is
# overridable via env so the production settings module can be imported
# on a dev machine (e.g. to run `check --deploy`) without that path
# existing. `delay=True` means the handler doesn't open the file until
# the first record is written.
# ---------------------------------------------------------------------------
LOG_DIR = config("LOG_DIR", default="/var/log/anjaneya")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/django.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "delay": True,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/django-error.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "level": "ERROR",
            "delay": True,
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["file", "console"], "level": "INFO"},
    "loggers": {
        "django.request": {
            "handlers": ["error_file"],
            "level": "WARNING",
            "propagate": True,
        },
        "apps": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# ---------------------------------------------------------------------------
# Sentry (optional — only initialised if SENTRY_DSN is set)
# ---------------------------------------------------------------------------
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=config("SENTRY_ENV", default="production"),
        traces_sample_rate=0.1,
        send_default_pii=False,
    )


# ---------------------------------------------------------------------------
# Admins / server email
# ---------------------------------------------------------------------------
ADMINS = [
    tuple(a.split(":"))
    for a in config("DJANGO_ADMINS", default="", cast=Csv())
    if ":" in a
]
SERVER_EMAIL = config("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)


# ---------------------------------------------------------------------------
# Celery — NOTE: no worker/beat process runs in this deployment.
#
# Step 10 was deployed with gunicorn-only systemd units (deliberate
# choice — see docs/deployment-audit.md). base.py's Celery defaults
# still apply: send_email_task.delay() pushes to Redis and returns, but
# nothing consumes the queue, so enquiry-notification emails and the
# periodic digests do NOT send in production until a worker unit is
# added. This is a known, documented limitation. Redis itself is still
# used as the Django cache backend above.
# ---------------------------------------------------------------------------
