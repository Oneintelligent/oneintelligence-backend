# sales/urls.py
from rest_framework import routers
from django.urls import path, include
from .views import AccountViewSet, LeadViewSet, OpportunityViewSet, ActivityViewSet, DashboardViewSet

router = routers.DefaultRouter()
router.register(r"accounts", AccountViewSet, basename="sales-accounts")
router.register(r"leads", LeadViewSet, basename="sales-leads")
router.register(r"opportunities", OpportunityViewSet, basename="sales-opportunities")
router.register(r"activities", ActivityViewSet, basename="sales-activities")
router.register(r"dashboard", DashboardViewSet, basename="sales-dashboard")  # ⭐ NEW


urlpatterns = [
    path("", include(router.urls)),  # NOT api/v1
]
