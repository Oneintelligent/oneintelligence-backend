"""
Consent Management URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsentViewSet

router = DefaultRouter()
router.register(r"consent", ConsentViewSet, basename="consent")

urlpatterns = [
    path("", include(router.urls)),
]

