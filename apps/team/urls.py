from rest_framework.routers import DefaultRouter

from .views import TeamMemberViewSet

router = DefaultRouter()
router.register("team", TeamMemberViewSet, basename="team")

urlpatterns = router.urls
