from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

from rest_framework.routers import DefaultRouter

# ================================
# ViewSets
# ================================
from app.onboarding.users.views import AOIViewSet as UserViewSet
from app.onboarding.companies.views import CompanyAOIViewSet


# ================================
# ROUTERS
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
    # ADMIN CONSOLE
    # -------------------------
    path("admin/", admin.site.urls),

    # -------------------------
    # API ROUTES (Users + Companies)
    # Base: /api/v1/
    # -------------------------
    path("api/v1/", include(router.urls)),

    # -------------------------
    # Subscriptions
    # /api/v1/subscriptions/
    # -------------------------
    path("api/v1/subscriptions/", include("app.subscriptions.urls")),

    # -------------------------
    # AI endpoints
    # -------------------------
    path("api/oneintelligentai/", include("app.oneintelligentai.urls")),

    # -------------------------
    # Swagger & Redoc
    # -------------------------
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui"
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc"
    ),
]
