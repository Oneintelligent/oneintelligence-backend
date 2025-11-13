import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets
from .models import Subscriptions
from .serializers import SubscriptionsSerializer
from app.utils.response import api_response
from rest_framework.permissions import AllowAny  # ✅ change this import

logger = logging.getLogger(__name__)


class SubscriptionsViewSet(viewsets.ModelViewSet):
    queryset = Subscriptions.objects.all().order_by('-created_date')
    serializer_class = SubscriptionsSerializer
    permission_classes = [AllowAny]  # ✅ anyone can access this endpoint

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        user_id = self.request.query_params.get("user_id")
        if company_id:
            queryset = queryset.filter(companyId=company_id)
        if user_id:
            queryset = queryset.filter(userId=user_id)
        return queryset

    def perform_create(self, serializer):
        plan = serializer.validated_data.get("plan")
        billing_type = serializer.validated_data.get("billing_type")

        # Price table
        plan_prices = {
            "Pro": {"Monthly": 1200, "Yearly": 12000},
            "Max": {"Monthly": 3000, "Yearly": 33000},
            "Ultra Max": {"Monthly": 6000, "Yearly": 66000},
        }

        # Free 90-day Max trial
        if plan == "Max":
            price_per_license = 0
            end_date = timezone.now() + timedelta(days=90)
        else:
            price_per_license = plan_prices[plan][billing_type]
            end_date = serializer.validated_data.get("end_date")

        serializer.save(
            price_per_license=price_per_license,
            start_date=timezone.now(),
            end_date=end_date,
        )

    def list(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            return api_response(0, "success", serializer.data)
        except Exception as e:
            logger.exception("Error listing subscriptions")
            return api_response(1, "failure", {}, "LIST_SUBSCRIPTIONS_ERROR", str(e))

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return api_response(0, "success", serializer.data)
        except Exception as e:
            logger.exception("Error creating subscription")
            return api_response(1, "failure", {}, "CREATE_SUBSCRIPTION_ERROR", str(e))

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(0, "success", serializer.data)
        except Exception as e:
            logger.exception("Error updating subscription")
            return api_response(1, "failure", {}, "UPDATE_SUBSCRIPTION_ERROR", str(e))

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(0, "success", serializer.data)
        except Exception as e:
            logger.exception("Error partially updating subscription")
            return api_response(1, "failure", {}, "PARTIAL_UPDATE_SUBSCRIPTION_ERROR", str(e))

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return api_response(0, "success", {})
        except Exception as e:
            logger.exception("Error deleting subscription")
            return api_response(1, "failure", {}, "DELETE_SUBSCRIPTION_ERROR", str(e))
