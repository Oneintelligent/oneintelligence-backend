from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionsViewSet, SubscriptionPlanViewSet

router = DefaultRouter()
router.register(r'subscriptions', SubscriptionsViewSet, basename='subscriptions')
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plans')

urlpatterns = [
    path('', include(router.urls)),
]
