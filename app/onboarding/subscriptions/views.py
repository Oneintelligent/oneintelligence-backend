from rest_framework import viewsets, permissions
from .models import Subscriptions, SubscriptionPlan
from .serializers import SubscriptionsSerializer, SubscriptionPlanSerializer
from rest_framework.permissions import AllowAny  # ✅ change this import

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all().order_by("id")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]  # ✅ anyone can access this endpoint


class SubscriptionsViewSet(viewsets.ModelViewSet):
    queryset = Subscriptions.objects.all().order_by("-created_date")
    serializer_class = SubscriptionsSerializer
    permission_classes = [AllowAny]  # ✅ anyone can access this endpoint
