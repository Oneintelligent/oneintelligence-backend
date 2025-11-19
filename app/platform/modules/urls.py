from rest_framework.routers import DefaultRouter

from .views import ModuleDefinitionViewSet, CompanyModuleViewSet

router = DefaultRouter()
router.register(r"modules/definitions", ModuleDefinitionViewSet, basename="module-definitions")
router.register(r"modules/company", CompanyModuleViewSet, basename="company-modules")

urlpatterns = router.urls

