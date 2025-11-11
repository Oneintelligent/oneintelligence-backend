from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import UserViewSet

# Initialize DRF router
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    # All user-related endpoints (signup, signin, signout, me, CRUD, etc.)
    path('', include(router.urls)),
]
