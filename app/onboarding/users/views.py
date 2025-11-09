import logging
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from .models import Users
from .serializers import UserSerializer
from app.onboarding.subscriptions.models import Subscriptions
from app.onboarding.subscriptions.serializers import SubscriptionsSerializer
from app.onboarding.companies.models import Company
from app.utils.response import api_response

logger = logging.getLogger(__name__)

class UsersViewSet(viewsets.ModelViewSet):
    queryset = Users.objects.all()
    serializer_class = UserSerializer

    # ------------------------------
    # Standard CRUD Methods
    # ------------------------------
    def list(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error listing users")
            return api_response(status_code=1, status="failure", data={}, error_code="LIST_USERS_ERROR", error_message=str(e))

    def retrieve(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_object())
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error retrieving user")
            return api_response(status_code=1, status="failure", data={}, error_code="RETRIEVE_USER_ERROR", error_message=str(e))

    def create(self, request, *args, **kwargs):
        """
        Create a user. If company exists, attach user.
        Optionally, create free 90-day Max subscription for MVP.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # If user has a company, create free 90-day Max subscription
            if user.companyId:
                end_date = timezone.now() + timezone.timedelta(days=90)
                Subscriptions.objects.create(
                    company=user.companyId,
                    user=user,
                    plan="Max",
                    billing_type="Monthly",
                    license_count=1,
                    start_date=timezone.now(),
                    end_date=end_date,
                    status="Active",
                )

            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error creating user")
            return api_response(status_code=1, status="failure", data={}, error_code="CREATE_USER_ERROR", error_message=str(e))

    def update(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_object(), data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error updating user")
            return api_response(status_code=1, status="failure", data={}, error_code="UPDATE_USER_ERROR", error_message=str(e))

    def partial_update(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error partially updating user")
            return api_response(status_code=1, status="failure", data={}, error_code="PARTIAL_UPDATE_USER_ERROR", error_message=str(e))

    def destroy(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return api_response(status_code=0, status="success", data={})
        except Exception as e:
            logger.exception("Error deleting user")
            return api_response(status_code=1, status="failure", data={}, error_code="DELETE_USER_ERROR", error_message=str(e))

    # ------------------------------
    # Activate Account Endpoint
    # ------------------------------
    @action(detail=True, methods=['post'])
    def activate_account(self, request, pk=None):
        """
        Activates the user account after payment.
        - Simulates payment for MVP
        - Sets user status to Active
        - Sets company status to Active
        - Creates a free 90-day Max subscription if not already present
        """
        try:
            user = self.get_object()

            if not user.companyId:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="NO_COMPANY_ERROR",
                    error_message="User is not associated with a company."
                )

            company = user.companyId

            # Simulate payment success (replace with real payment gateway later)
            payment_success = True
            if not payment_success:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="PAYMENT_FAILED",
                    error_message="Payment was not successful."
                )

            # Activate user and company
            user.status = Users.Status.ACTIVE
            user.save()
            company.status = Company.StatusChoices.ACTIVE
            company.save()

            # Create free 90-day Max subscription if none exists
            if not Subscriptions.objects.filter(company=company, user=user, status="Active").exists():
                end_date = timezone.now() + timezone.timedelta(days=90)
                Subscriptions.objects.create(
                    company=company,
                    user=user,
                    plan="Max",
                    billing_type="Monthly",
                    license_count=1,
                    start_date=timezone.now(),
                    end_date=end_date,
                    status="Active",
                )

            subscription = Subscriptions.objects.filter(company=company, user=user, status="Active").first()

            return api_response(
                status_code=0,
                status="success",
                data={
                    "user": UserSerializer(user).data,
                    "company": {
                        "companyId": company.companyId,
                        "name": company.name,
                        "status": company.status
                    },
                    "subscription": SubscriptionsSerializer(subscription).data if subscription else None
                }
            )

        except Exception as e:
            logger.exception("Error activating account")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="ACTIVATE_ACCOUNT_ERROR",
                error_message=str(e)
            )
