from datetime import timedelta

import django_filters as df
from django.db.models import Exists, OuterRef
from django.utils import timezone

from .models import Project, ProjectImage


class ProjectFilter(df.FilterSet):
    """Filters for the /projects list endpoint.

    Param names match the live UI where one exists; the rest are
    documented in docs/search-spec.md as forward-looking knobs the
    frontend can adopt without further backend work.
    """

    # Category pills support multi-value via CSV: ?category=residential,commercial
    category = df.BaseInFilter(
        field_name="category__slug", lookup_expr="in",
    )
    city = df.BaseInFilter(field_name="city__slug", lookup_expr="in")
    developer = df.CharFilter(field_name="developer__slug", lookup_expr="iexact")
    status = df.CharFilter(lookup_expr="iexact")
    is_featured = df.BooleanFilter()

    # Price range — single-bound on price_starting_lacs because the model
    # stores a starting price (the upper bound is "from X onwards").
    price_min = df.NumberFilter(field_name="price_starting_lacs", lookup_expr="gte")
    price_max = df.NumberFilter(field_name="price_starting_lacs", lookup_expr="lte")

    posted_within_days = df.NumberFilter(method="filter_posted_within_days")
    has_image = df.BooleanFilter(method="filter_has_image")

    class Meta:
        model = Project
        fields = (
            "category", "city", "developer", "status", "is_featured",
            "price_min", "price_max",
            "posted_within_days", "has_image",
        )

    def filter_posted_within_days(self, queryset, name, value):
        if value is None or value <= 0:
            return queryset
        cutoff = timezone.now() - timedelta(days=int(value))
        return queryset.filter(published_at__gte=cutoff)

    def filter_has_image(self, queryset, name, value):
        if value is None:
            return queryset
        has = Exists(ProjectImage.objects.filter(project_id=OuterRef("pk")))
        return queryset.annotate(_has_img=has).filter(_has_img=value)
