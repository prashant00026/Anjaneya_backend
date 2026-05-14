"""
Production settings.

DEBUG is off, Postgres is the backing database, and standard
security headers are enabled.
"""

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

# Postgres via individual DB_* vars from the environment.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# Security headers / HTTPS hardening.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"


# ---------------------------------------------------------------------------
# S3 media storage (django-storages) — DISABLED.
# ---------------------------------------------------------------------------
# TODO: enable when deploying. To switch over:
#   1. Add "storages" to INSTALLED_APPS in base.py
#   2. Set the env vars below in the deployment environment
#   3. Uncomment the block.
#
# from .base import STORAGES  # noqa: E402
# STORAGES = {
#     **STORAGES,
#     "default": {
#         "BACKEND": "storages.backends.s3.S3Storage",
#         "OPTIONS": {
#             "bucket_name": config("AWS_STORAGE_BUCKET_NAME"),
#             "region_name": config("AWS_S3_REGION_NAME", default="ap-south-1"),
#             "access_key": config("AWS_ACCESS_KEY_ID"),
#             "secret_key": config("AWS_SECRET_ACCESS_KEY"),
#             "querystring_auth": False,
#             "file_overwrite": False,
#             "object_parameters": {"CacheControl": "max-age=86400"},
#         },
#     },
# }
