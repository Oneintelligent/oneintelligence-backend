from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.company_products_viewset import CompanyProductsViewSet
from .views.company_product_field_viewset import CompanyProductFieldViewSet

router = DefaultRouter()
router.register(r'company-products', CompanyProductsViewSet, basename='company-products')
router.register(r'company-product-fields', CompanyProductFieldViewSet, basename='company-product-fields')

urlpatterns = [
    path('', include(router.urls)),
]
