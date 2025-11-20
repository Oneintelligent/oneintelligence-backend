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
from app.platform.accounts.views import UserViewSet
from app.platform.companies.views import CompanyAOIViewSet

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
    # -------------------------
    # Platform services
    # -------------------------
    path("api/v1/", include("app.platform.teams.urls")),
    path("api/v1/", include("app.platform.modules.urls")),
    path("api/v1/", include("app.platform.licensing.urls")),
    path("api/v1/", include("app.platform.flac.urls")),
    path("api/v1/", include("app.platform.onboarding.urls")),
    path("api/v1/subscriptions/", include("app.platform.subscriptions.urls")),

    # -------------------------
    # Workspace modules
    # -------------------------
    path("api/v1/", include("app.workspace.sales.urls")),
    path("api/v1/", include("app.workspace.projects.urls")),
    path("api/v1/", include("app.workspace.tasks.urls")),
    path("api/v1/", include("app.workspace.support.urls")),
    path("api/v1/", include("app.workspace.dashboard.urls")),

    # -------------------------
    # OneIntelligent AI endpoints
    # /api/oneintelligentai/
    # -------------------------
    path("api/oneintelligentai/", include("app.ai.oneintelligentai.urls")),

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
