# app/subscriptions/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SubscriptionPlanViewSet, SubscriptionsViewSet

router = DefaultRouter()

# -------------------------
# Subscription Plan APIs
# Public read, admin write
# -------------------------
router.register(
    r"plans",
    SubscriptionPlanViewSet,
    basename="subscription-plans"
)

# -------------------------
# Subscriptions APIs
# Company subscription / billing
# -------------------------
router.register(
    r"",
    SubscriptionsViewSet,
    basename="subscriptions"
)

urlpatterns = [
    # Nothing extra (router handles everything)
]

urlpatterns += router.urls
