from rest_framework.routers import DefaultRouter

from .views import RoleFieldPolicyViewSet

router = DefaultRouter()
router.register(r"flac/policies", RoleFieldPolicyViewSet, basename="flac-policies")

urlpatterns = router.urls
