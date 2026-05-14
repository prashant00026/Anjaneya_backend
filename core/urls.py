"""
Root URL configuration for the Anjaneya backend.

API surface:
    /admin/             Django admin
    /api/v1/            Versioned API root (apps register routers here)
    /api/schema/        OpenAPI 3 schema (JSON)
    /api/docs/          Swagger UI
    /api/redoc/         ReDoc UI
    /health/            Liveness probe
    /health/ready/      Readiness probe (DB + cache)
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from common.views import health, health_ready

api_v1_patterns = [
    path("", include("catalog.urls")),
    path("", include("projects.urls")),
    path("", include("enquiries.urls")),
    path("", include("team.urls")),
    path("", include("testimonials.urls")),
    path("", include("site_settings.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
    # API schema & docs.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Health checks — nginx, uptime monitors, and deploy.sh poll these.
    path("health/", health, name="health"),
    path("health/ready/", health_ready, name="health-ready"),
]

# Serve uploaded media in development. In production, media should be
# served by the reverse proxy (or S3 via django-storages).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # django-debug-toolbar is dev-only; mount its URLs when DEBUG is on
    # AND the package is actually installed (so production.py isn't
    # accidentally importing a missing dependency).
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except ImportError:
        pass
