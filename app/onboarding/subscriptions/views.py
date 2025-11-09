import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets, status
from .models import Subscriptions
from .serializers import SubscriptionsSerializer
from app.onboarding.users.serializers import UsersSerializer
from app.onboarding.companies.serializers import CompanySerializer
from app.utils.response import api_response

logger = logging.getLogger(__name__)

class SubscriptionsViewSet(viewsets.ModelViewSet):
    queryset = Subscriptions.objects.all()
    serializer_class = SubscriptionsSerializer

    def get_queryset(self):
        """
        Optionally filter subscriptions by company_id or user_id via query params.
        """
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        user_id = self.request.query_params.get("user_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset

    def perform_create(self, serializer):
        """
        Automatically handle free 90-day Max plan for MVP.
        """
        plan = serializer.validated_data.get("plan")
        billing_type = serializer.validated_data.get("billing_type")

        # Determine price per license
        plan_prices = {
            "Pro": {"Monthly": 1200, "Yearly": 12000},
            "Max": {"Monthly": 3000, "Yearly": 33000},
            "Ultra Max": {"Monthly": 6000, "Yearly": 66000},
        }

        price_per_license = plan_prices[plan][billing_type]

        # Apply free 90-day logic for Max plan
        if plan == "Max":
            price_per_license = 0
            end_date = timezone.now() + timedelta(days=90)
        else:
            end_date = serializer.validated_data.get("end_date")

        serializer.save(
            price_per_license=price_per_license,
            start_date=timezone.now(),
            end_date=end_date
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = SubscriptionsSerializer(queryset, many=True)
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error listing subscriptions")
            return api_response(status_code=1, status="failure", data={}, error_code="LIST_SUBSCRIPTIONS_ERROR", error_message=str(e))

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error creating subscription")
            return api_response(status_code=1, status="failure", data={}, error_code="CREATE_SUBSCRIPTION_ERROR", error_message=str(e))

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=False)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error updating subscription")
            return api_response(status_code=1, status="failure", data={}, error_code="UPDATE_SUBSCRIPTION_ERROR", error_message=str(e))

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error partially updating subscription")
            return api_response(status_code=1, status="failure", data={}, error_code="PARTIAL_UPDATE_SUBSCRIPTION_ERROR", error_message=str(e))

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return api_response(status_code=0, status="success", data={})
        except Exception as e:
            logger.exception("Error deleting subscription")
            return api_response(status_code=1, status="failure", data={}, error_code="DELETE_SUBSCRIPTION_ERROR", error_message=str(e))
