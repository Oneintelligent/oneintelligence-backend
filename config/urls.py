from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

from rest_framework.routers import DefaultRouter

# Users router
from app.onboarding.users.views import UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    # ================================
    # ADMIN
    # ================================
    path("admin/", admin.site.urls),

    # ================================
    # USERS (signup/signin/me etc.)
    # Base: /api/v1/users/
    # ================================
    path("api/v1/", include(router.urls)),

    # ================================
    # COMPANY APIs (setup/settings/team/modules/subscription/activate/discount)
    # Base: /api/v1/company/
    # ================================
    path("api/v1/company/", include("app.onboarding.companies.urls")),

    # ================================
    # SUBSCRIPTIONS
    # Base: /api/v1/subscriptions/
    # ================================
    path("api/v1/subscriptions/", include("app.subscriptions.urls")),

    # ================================
    # AI ENDPOINTS
    # ================================
    path("api/oneintelligentai/", include("app.oneintelligentai.urls")),

    # ================================
    # API SCHEMA & SWAGGER
    # ================================
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
