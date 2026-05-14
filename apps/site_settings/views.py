from rest_framework import generics

from .models import CmsPage, SiteSettings
from .serializers import CmsPageSerializer, SiteSettingsSerializer


class SiteSettingsView(generics.RetrieveAPIView):
    """Singleton — returns the only SiteSettings row."""

    serializer_class = SiteSettingsSerializer

    def get_object(self):
        return SiteSettings.load()


class CmsPageDetailView(generics.RetrieveAPIView):
    queryset = CmsPage.objects.filter(is_published=True)
    serializer_class = CmsPageSerializer
    lookup_field = "slug"
