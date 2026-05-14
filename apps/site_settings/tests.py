from rest_framework import status
from rest_framework.test import APITestCase

from .models import CmsPage, SiteSettings


class SiteSettingsSmokeTests(APITestCase):
    def test_settings_auto_creates_and_returns(self):
        r = self.client.get("/api/v1/site/settings/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(r.data["hero_stat_clients"], "98+")

    def test_cms_page_published(self):
        CmsPage.objects.create(slug="about", title="About", body="Hi")
        r = self.client.get("/api/v1/site/pages/about/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["title"], "About")

    def test_cms_page_unpublished_404(self):
        CmsPage.objects.create(slug="draft", title="Draft", body="", is_published=False)
        r = self.client.get("/api/v1/site/pages/draft/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
