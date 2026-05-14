from rest_framework import viewsets

from .models import Amenity, Category, City, Developer
from .serializers import (
    AmenitySerializer,
    CategorySerializer,
    CitySerializer,
    DeveloperSerializer,
)


class _ActiveReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"

    def get_queryset(self):
        return self.queryset.filter(is_active=True)


class CityViewSet(_ActiveReadOnlyViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer


class CategoryViewSet(_ActiveReadOnlyViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class DeveloperViewSet(_ActiveReadOnlyViewSet):
    queryset = Developer.objects.all()
    serializer_class = DeveloperSerializer


class AmenityViewSet(_ActiveReadOnlyViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
