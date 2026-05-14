from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FloorPlanViewSet, ProjectImageViewSet, ProjectViewSet


router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")


# --- Nested admin-only media endpoints --------------------------------
# /api/v1/projects/<project_pk>/images/
# /api/v1/projects/<project_pk>/images/<pk>/
# /api/v1/projects/<project_pk>/floor-plans/
# /api/v1/projects/<project_pk>/floor-plans/<pk>/
_image_list = ProjectImageViewSet.as_view({
    "get": "list", "post": "create",
})
_image_detail = ProjectImageViewSet.as_view({
    "get": "retrieve", "patch": "partial_update",
    "put": "update", "delete": "destroy",
})
_floor_list = FloorPlanViewSet.as_view({
    "get": "list", "post": "create",
})
_floor_detail = FloorPlanViewSet.as_view({
    "get": "retrieve", "patch": "partial_update",
    "put": "update", "delete": "destroy",
})

nested_media = [
    path("projects/<int:project_pk>/images/", _image_list, name="project-images"),
    path("projects/<int:project_pk>/images/<int:pk>/", _image_detail, name="project-image-detail"),
    path("projects/<int:project_pk>/floor-plans/", _floor_list, name="project-floor-plans"),
    path("projects/<int:project_pk>/floor-plans/<int:pk>/", _floor_detail, name="project-floor-plan-detail"),
]


# The numeric-id alias for project detail must come BEFORE the router's
# slug pattern, otherwise `<slug>` (regex `[^/.]+`) swallows pure-int paths.
urlpatterns = (
    nested_media
    + [
        path(
            "projects/<int:pk>/",
            ProjectViewSet.as_view({"get": "retrieve"}),
            name="project-by-id",
        ),
    ]
    + router.urls
)
