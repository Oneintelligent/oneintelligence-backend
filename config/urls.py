from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

# User ViewSet router
from app.onboarding.users.views import UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")


urlpatterns = [
    # ================================
    # API ROUTES
    # ================================
    path("api/v1/", include(router.urls)),

    # Company Setup / Settings APIs
    path("api/v1/company/", include("app.onboarding.companies.urls")),

    # Products (if enabled)
    # path("api/v1/products/", include("app.onboarding.products.urls")),

    # Subscriptions
    path("api/v1/subscriptions/", include("app.subscriptions.urls")),


    # Oneintelligent AI endpoints
    path('api/oneintelligentai/', include('app.oneintelligentai.urls')),

    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    
]
