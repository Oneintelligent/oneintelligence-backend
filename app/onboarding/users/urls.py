from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.onboarding.users.views import AOIViewSet

router = DefaultRouter()
router.register(r'users', AOIViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
]
