from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionsViewSet

router = DefaultRouter()
router.register(r'subscriptions', SubscriptionsViewSet, basename='subscriptions')

urlpatterns = [
    path('', include(router.urls)),
]
