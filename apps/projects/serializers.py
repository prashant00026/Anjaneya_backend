from rest_framework import serializers

from catalog.serializers import (
    AmenitySerializer,
    CategorySerializer,
    CitySerializer,
    DeveloperSerializer,
)

from .models import (
    FloorPlan,
    Project,
    ProjectHighlight,
    ProjectImage,
    ProjectStat,
)


def _abs(request, file_field):
    """Return an absolute URL for any FieldFile (image, imagekit, file)."""
    if not file_field:
        return None
    url = getattr(file_field, "url", None)
    if not url:
        return None
    return request.build_absolute_uri(url) if request else url


class ProjectImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    medium = serializers.SerializerMethodField()
    large = serializers.SerializerMethodField()

    class Meta:
        model = ProjectImage
        fields = (
            "id", "image", "thumbnail", "medium", "large",
            "caption", "alt_text", "display_order", "is_primary",
        )

    def _req(self):
        return self.context.get("request")

    def get_image(self, obj):
        return _abs(self._req(), obj.image)

    def get_thumbnail(self, obj):
        return _abs(self._req(), obj.thumbnail) if obj.image else None

    def get_medium(self, obj):
        return _abs(self._req(), obj.medium) if obj.image else None

    def get_large(self, obj):
        return _abs(self._req(), obj.large) if obj.image else None


class FloorPlanSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = FloorPlan
        fields = (
            "id", "file", "label", "caption", "alt_text", "display_order",
        )

    def get_file(self, obj):
        return _abs(self.context.get("request"), obj.file)


class ProjectHighlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectHighlight
        fields = ("id", "text", "display_order")


class ProjectStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStat
        fields = ("id", "label", "value", "icon_key", "display_order")


class _CoverMixin:
    """Shared cover-image variant fields for both list and detail."""

    def _req(self):
        return self.context.get("request")

    def get_cover_image(self, obj):
        return _abs(self._req(), obj.cover_image)

    def get_cover_thumbnail(self, obj):
        return _abs(self._req(), obj.cover_thumbnail) if obj.cover_image else None

    def get_cover_medium(self, obj):
        return _abs(self._req(), obj.cover_medium) if obj.cover_image else None

    def get_cover_large(self, obj):
        return _abs(self._req(), obj.cover_large) if obj.cover_image else None


class ProjectListSerializer(_CoverMixin, serializers.ModelSerializer):
    """Lightweight shape for the /projects grid — cover thumbnail + count only."""

    category = CategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    cover_image = serializers.SerializerMethodField()
    cover_thumbnail = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id", "slug", "title", "tagline",
            "category", "city", "locality",
            "status", "property_type",
            "price_display", "size_display",
            "cover_image", "cover_thumbnail", "image_count",
            "is_featured", "published_at",
        )

    def get_image_count(self, obj):
        # Prefer the annotated value (avoids N+1 on the list endpoint);
        # fall back to a count() for callers that pass an un-annotated qs.
        annotated = getattr(obj, "image_count", None)
        return annotated if annotated is not None else obj.images.count()


class ProjectDetailSerializer(_CoverMixin, serializers.ModelSerializer):
    """Full shape for /projects/<slug> — every variant + nested children."""

    category = CategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    developer = DeveloperSerializer(read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    images = ProjectImageSerializer(many=True, read_only=True)
    floor_plans = FloorPlanSerializer(many=True, read_only=True)
    highlights = ProjectHighlightSerializer(many=True, read_only=True)
    stats = ProjectStatSerializer(many=True, read_only=True)

    cover_image = serializers.SerializerMethodField()
    cover_thumbnail = serializers.SerializerMethodField()
    cover_medium = serializers.SerializerMethodField()
    cover_large = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id", "slug", "title", "tagline",
            "category", "city", "locality", "developer",
            "status", "property_type",
            "description",
            "price_starting_lacs", "price_display", "size_display",
            "rera_number", "map_embed_url",
            "cover_image", "cover_thumbnail", "cover_medium", "cover_large",
            "amenities", "images", "floor_plans", "highlights", "stats",
            "is_featured", "featured_order", "published_at",
        )


# -- Create serializers (admin-only API) --------------------------------


class ProjectImageCreateSerializer(serializers.ModelSerializer):
    """Used by POST /api/v1/projects/<id>/images/ — `project` injected from URL."""

    class Meta:
        model = ProjectImage
        fields = (
            "id", "image", "caption", "alt_text", "display_order", "is_primary",
        )
        read_only_fields = ("id",)


class FloorPlanCreateSerializer(serializers.ModelSerializer):
    """Used by POST /api/v1/projects/<id>/floor-plans/."""

    class Meta:
        model = FloorPlan
        fields = ("id", "file", "label", "caption", "alt_text", "display_order")
        read_only_fields = ("id",)
