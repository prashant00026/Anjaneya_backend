from django.urls import path

from .views import CmsPageDetailView, SiteSettingsView

urlpatterns = [
    path("site/settings/", SiteSettingsView.as_view(), name="site-settings"),
    path("site/pages/<slug:slug>/", CmsPageDetailView.as_view(), name="site-page-detail"),
]
