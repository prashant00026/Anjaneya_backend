"""
Base settings shared by all environments.

Environment-specific overrides live in:
    - core/settings/development.py
    - core/settings/production.py
"""

import sys
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# BASE_DIR points at the project root (the folder containing manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Make `apps/` importable so apps can be referenced as `from <appname>...`
# instead of `from apps.<appname>...`.
sys.path.insert(0, str(BASE_DIR / "apps"))


# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    # django-unfold MUST come before `django.contrib.admin` because it
    # overrides admin templates at import time.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "unfold.contrib.simple_history",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "imagekit",
    "django_celery_beat",
    "django_celery_results",
    "import_export",
    "simple_history",
]

LOCAL_APPS = [
    "catalog",
    "projects",
    "enquiries",
    "team",
    "testimonials",
    "site_settings",
    "notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files in production without a separate server.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # CORS must come before CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # simple_history: stamps the acting user onto every Historical* row.
    "simple_history.middleware.HistoryRequestMiddleware",
]


# ---------------------------------------------------------------------------
# URL / WSGI / ASGI
# ---------------------------------------------------------------------------
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# No custom user model — this is a listing-only site with no public signup.
# Django's built-in `auth.User` is used for admin / staff login at /admin/.


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# ---------------------------------------------------------------------------
# File uploads & media validation
# ---------------------------------------------------------------------------
# Files up to this size stream into memory; larger ones spool to a temp file.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
# Hard cap on total upload body size (multipart with several files).
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024  # 30 MB

# Limits consumed by apps/common/validators.py.
MAX_IMAGE_SIZE_MB = 5
MAX_FLOOR_PLAN_SIZE_MB = 10
MIN_IMAGE_DIMENSIONS = (400, 300)
MAX_IMAGE_DIMENSIONS = (8000, 8000)
ALLOWED_IMAGE_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
ALLOWED_FLOOR_PLAN_MIME_TYPES = (
    "image/jpeg", "image/png", "image/webp", "application/pdf",
)

# imagekit: generate thumbnail/medium/large derivatives on first request.
IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY = "imagekit.cachefiles.strategies.Optimistic"


# ---------------------------------------------------------------------------
# django-unfold — admin theme
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Anjaneya Admin",
    "SITE_HEADER": "Anjaneya Real Estate",
    "SITE_SUBHEADER": "Listings, enquiries, content",
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "DASHBOARD_CALLBACK": "core.admin_dashboard.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Listings",
                "separator": True,
                "items": [
                    {
                        "title": "Projects",
                        "icon": "domain",
                        "link": "/admin/projects/project/",
                    },
                    {
                        "title": "Cities",
                        "icon": "location_city",
                        "link": "/admin/catalog/city/",
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/catalog/category/",
                    },
                    {
                        "title": "Developers",
                        "icon": "engineering",
                        "link": "/admin/catalog/developer/",
                    },
                    {
                        "title": "Amenities",
                        "icon": "pool",
                        "link": "/admin/catalog/amenity/",
                    },
                ],
            },
            {
                "title": "Inquiries",
                "separator": True,
                "items": [
                    {
                        "title": "Enquiries",
                        "icon": "mail",
                        "link": "/admin/enquiries/enquiry/",
                    },
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "items": [
                    {
                        "title": "Site settings",
                        "icon": "settings",
                        "link": "/admin/site_settings/sitesettings/",
                    },
                    {
                        "title": "CMS pages",
                        "icon": "article",
                        "link": "/admin/site_settings/cmspage/",
                    },
                    {
                        "title": "Team",
                        "icon": "groups",
                        "link": "/admin/team/teammember/",
                    },
                    {
                        "title": "Testimonials",
                        "icon": "format_quote",
                        "link": "/admin/testimonials/testimonial/",
                    },
                ],
            },
            {
                "title": "System",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/auth/user/",
                    },
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": "/admin/auth/group/",
                    },
                    {
                        "title": "Failed notifications",
                        "icon": "report",
                        "link": "/admin/notifications/failednotification/",
                    },
                    {
                        "title": "Periodic tasks",
                        "icon": "schedule",
                        "link": "/admin/django_celery_beat/periodictask/",
                    },
                    {
                        "title": "Task results",
                        "icon": "task_alt",
                        "link": "/admin/django_celery_results/taskresult/",
                    },
                ],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # SessionAuthentication lets admins call admin-gated media endpoints
        # straight from a browser after logging into /admin/.
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Listing site: API is public-read. Writes happen via /admin/ only.
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        # Tight scope for the public POST /api/v1/enquiries/ — see
        # apps/common/throttles.py:EnquiryThrottle.
        "enquiry": "10/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ---------------------------------------------------------------------------
# drf-spectacular (Swagger / OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Anjaneya Real Estate API",
    "DESCRIPTION": "Backend API for the Anjaneya Real Estate platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000",
    cast=Csv(),
)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# Default to Django's SMTP backend; development.py overrides to console.
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=25, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default="no-reply@anjaneyaglobalrealty.com",
)
# CSV of admin emails that receive new-inquiry notifications. Empty = none.
INQUIRY_NOTIFICATION_EMAILS = config(
    "INQUIRY_NOTIFICATION_EMAILS", default="", cast=Csv(),
)


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
# Broker: Redis by default; override via env. Database 1 keeps queue keys
# out of database 0 if you happen to share a Redis instance.
CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL", default="redis://localhost:6379/1",
)
# Result backend: store task results in the Django DB via django-celery-results
# so admins can see successes/failures without trawling logs.
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"

# Beat (periodic-task scheduler) reads schedule from the DB so admins can
# tune cron expressions live via /admin/django_celery_beat/.
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 5 * 60          # hard kill at 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60     # soft warning at 4 minutes
# `acks_late` + `reject_on_worker_lost` re-queue tasks if a worker dies
# mid-execution, paired with prefetch=1 so a slow task doesn't starve others.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Tests run tasks inline so we don't need a worker process. Both base
# and development.py have this off; tests flip it on via override_settings.
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} - {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "django.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
