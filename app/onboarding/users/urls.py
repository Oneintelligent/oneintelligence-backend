# app/sales/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    AccountViewSet,
    LeadViewSet,
    OpportunityViewSet,
    ActivityViewSet,
)

router = DefaultRouter()

# ---------------------
# SALES ROUTES
# ---------------------
router.register(r"sales/accounts", AccountViewSet, basename="sales-accounts")
router.register(r"sales/leads", LeadViewSet, basename="sales-leads")
router.register(r"sales/opportunities", OpportunityViewSet, basename="sales-opportunities")
router.register(r"sales/activities", ActivityViewSet, basename="sales-activities")

urlpatterns = [
    path("", include(router.urls)),
]
