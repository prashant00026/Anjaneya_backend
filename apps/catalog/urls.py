from rest_framework.routers import DefaultRouter

from .views import AmenityViewSet, CategoryViewSet, CityViewSet, DeveloperViewSet

router = DefaultRouter()
router.register("cities", CityViewSet, basename="city")
router.register("categories", CategoryViewSet, basename="category")
router.register("developers", DeveloperViewSet, basename="developer")
router.register("amenities", AmenityViewSet, basename="amenity")

urlpatterns = router.urls
