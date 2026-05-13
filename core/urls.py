"""
Root URL configuration for the Anjaneya backend.

API surface:
    /admin/             Django admin
    /api/v1/            Versioned API root (apps will register routers here)
    /api/schema/        OpenAPI 3 schema (JSON)
    /api/docs/          Swagger UI
    /api/redoc/         ReDoc UI
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
from rest_framework.routers import DefaultRouter

# Empty router for now — app viewsets will be registered here in step 2.
router = DefaultRouter()

api_v1_patterns = [
    path("", include(router.urls)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
    # API schema & docs.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve uploaded media in development. In production, media should be
# served by the reverse proxy (or S3 via django-storages).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
