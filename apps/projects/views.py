from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import mixins, parsers, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import ProjectFilter
from .models import FloorPlan, Project, ProjectImage
from .serializers import (
    FloorPlanCreateSerializer,
    FloorPlanSerializer,
    ProjectDetailSerializer,
    ProjectImageCreateSerializer,
    ProjectImageSerializer,
    ProjectListSerializer,
)


# Columns the list serializer actually renders. Using `.only(...)` keeps
# the SELECT narrow and avoids loading `description` (free text) on the
# grid endpoint.
_LIST_COLUMNS = (
    "id", "slug", "title", "tagline", "status", "property_type",
    "locality", "price_display", "size_display",
    "cover_image", "is_featured", "featured_order", "published_at",
    "category_id", "city_id", "developer_id",
    # imagekit specs read from cover_image; the model field name is enough.
)


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """Public read-only project endpoint.

    Detail resolves by either slug (default) or numeric id — the URLconf
    routes `/<slug>/` and `/<int:pk>/` to the same view.
    """

    filterset_class = ProjectFilter
    search_fields = ("title", "locality", "tagline")
    ordering_fields = (
        "published_at", "featured_order", "price_starting_lacs", "title",
    )
    ordering = ("-published_at", "-id")
    lookup_field = "slug"

    def get_queryset(self):
        base = Project.objects.filter(is_published=True)
        # List + featured: light SELECT, no detail-only prefetches, but
        # annotate `image_count` so the serializer doesn't N+1.
        if self.action in ("list", "featured", "by_ids"):
            return (
                base.only(*_LIST_COLUMNS)
                .select_related("category", "city")
                .annotate(image_count=Count("images", distinct=True))
            )
        # Retrieve + everything else: full prefetch tree for the detail page.
        return (
            base.select_related("category", "city", "developer")
            .prefetch_related(
                "amenities", "images", "floor_plans", "highlights", "stats",
            )
        )

    def get_serializer_class(self):
        if self.action in ("list", "featured", "by_ids"):
            return ProjectListSerializer
        return ProjectDetailSerializer

    def get_object(self):
        # Support both /projects/<slug>/ and /projects/<int:pk>/.
        qs = self.filter_queryset(self.get_queryset())
        if "pk" in self.kwargs and self.kwargs.get("pk") is not None:
            obj = get_object_or_404(qs, pk=self.kwargs["pk"])
        else:
            obj = get_object_or_404(qs, slug=self.kwargs[self.lookup_field])
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=["get"])
    def featured(self, request):
        qs = self.get_queryset().filter(is_featured=True).order_by(
            "featured_order", "-id",
        )[:6]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="by-ids")
    def by_ids(self, request):
        """Bulk-fetch projects by id, preserving the order in the query.

        Frontend stores recently-viewed ids in localStorage and calls this
        endpoint to hydrate them. Capped at 20 ids; unknown ids are silently
        dropped; only published projects come back. Cached for 5 minutes
        per unique requested id set.
        """
        from django.core.cache import cache

        raw = (request.query_params.get("ids") or "").strip()
        if not raw:
            return Response([])

        # Parse, dedupe (preserving first-occurrence order), clamp at 20.
        seen, ordered_ids = set(), []
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok or tok in seen:
                continue
            try:
                pid = int(tok)
            except ValueError:
                continue
            seen.add(tok)
            ordered_ids.append(pid)
            if len(ordered_ids) >= 20:
                break

        if not ordered_ids:
            return Response([])

        # Cache key uses the canonical ordered tuple.
        cache_key = f"projects:by-ids:{','.join(str(i) for i in ordered_ids)}"
        cached = None
        try:
            cached = cache.get(cache_key)
        except Exception:
            # Graceful degradation if the cache backend is down.
            cached = None
        if cached is not None:
            return Response(cached)

        qs = self.get_queryset().filter(pk__in=ordered_ids)
        by_pk = {p.pk: p for p in qs}
        ordered = [by_pk[pid] for pid in ordered_ids if pid in by_pk]
        data = self.get_serializer(ordered, many=True).data

        try:
            cache.set(cache_key, data, timeout=60 * 5)
        except Exception:
            pass
        return Response(data)


class _AdminMediaMixin:
    """Admin-only multipart media endpoints scoped to a parent project."""

    permission_classes = (permissions.IsAdminUser,)
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

    # Subclass overrides:
    parent_lookup_kwarg = "project_pk"
    parent_attr = "project"

    def _get_project(self):
        return get_object_or_404(Project, pk=self.kwargs[self.parent_lookup_kwarg])

    def get_queryset(self):
        return super().get_queryset().filter(**{self.parent_attr: self._get_project()})

    def perform_create(self, serializer):
        serializer.save(**{self.parent_attr: self._get_project()})


class ProjectImageViewSet(
    _AdminMediaMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-only CRUD for project gallery images, scoped to a project."""

    queryset = ProjectImage.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectImageCreateSerializer
        return ProjectImageSerializer


class FloorPlanViewSet(
    _AdminMediaMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-only CRUD for floor plans, scoped to a project."""

    queryset = FloorPlan.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return FloorPlanCreateSerializer
        return FloorPlanSerializer
