from rest_framework.routers import DefaultRouter

from .views import ModuleDefinitionViewSet, CompanyModuleViewSet

router = DefaultRouter()
router.register(r"products/definitions", ModuleDefinitionViewSet, basename="product-definitions")
router.register(r"products/company", CompanyModuleViewSet, basename="company-products")

urlpatterns = router.urls

