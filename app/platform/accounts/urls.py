# app/platform/accounts/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("api/v1/", include(router.urls)),
]
