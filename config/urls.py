from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from rest_framework.routers import DefaultRouter

# ================================
# ViewSets
# ================================
from app.onboarding.users.views import AOIViewSet as UserViewSet
from app.onboarding.companies.views import CompanyAOIViewSet

# ================================
# ROUTER INITIALIZATION
# ================================
router = DefaultRouter()

# /api/v1/users/...
router.register(r"users", UserViewSet, basename="users")

# /api/v1/companies/...
router.register(r"companies", CompanyAOIViewSet, basename="companies")

# ================================
# URL PATTERNS
# ================================
urlpatterns = [

    # -------------------------
    # Django Admin
    # -------------------------
    path("admin/", admin.site.urls),

    # -------------------------
    # Users + Companies
    # Base: /api/v1/
    # -------------------------
    path("api/v1/", include(router.urls)),

    # -------------------------
    # Teams Module
    # /api/v1/teams/
    # -------------------------
    path("api/v1/", include("app.teams.urls")),

    # -------------------------
    # Sales Module
    # /api/v1/sales/
    # -------------------------
    path("api/v1/", include("app.sales.urls")),

    # -------------------------
    # Subscriptions
    # /api/v1/subscriptions/
    # -------------------------
    path("api/v1/subscriptions/", include("app.subscriptions.urls")),

    # -------------------------
    # OneIntelligent AI endpoints
    # /api/oneintelligentai/
    # -------------------------
    path("api/oneintelligentai/", include("app.oneintelligentai.urls")),

    # -------------------------
    # OpenAPI / Swagger / Redoc
    # -------------------------
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
