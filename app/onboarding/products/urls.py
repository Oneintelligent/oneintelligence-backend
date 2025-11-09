from rest_framework.routers import DefaultRouter
from app.onboarding.products.company_product_field_view import CompanyProductFieldViewSet
from app.onboarding.products.company_products_view import CompanyProductsViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r"company-products", CompanyProductsViewSet, basename="company-products")
router.register(r"company-product-fields", CompanyProductFieldViewSet, basename="company-product-fields")


urlpatterns = [
    path('', include(router.urls)),
]

