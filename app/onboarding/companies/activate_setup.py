# app/onboarding/companies/activate_setup.py
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.utils.response import api_response
from app.onboarding.companies.models import Company
from app.subscriptions.models import Subscriptions
from app.onboarding.companies.permissions import is_owner, is_platform_admin
from app.onboarding.companies.serializers import CompanyActivateSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Company Activation"],
    summary="Activate company setup (finalize onboarding)",
    description=(
        "Performs final validations (owner only) and activates the subscription & company. "
        "Checks license_count >= total users and marks onboarding complete.\n\n"
        "Authentication: `Authorization: Bearer <access_token>`"
    ),
    request=CompanyActivateSerializer,
    responses={
        200: OpenApiResponse(description="Activated"),
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Forbidden"),
        404: OpenApiResponse(description="Not found"),
    }
)
class CompanyActivateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_company(self, companyId):
        return Company.objects.filter(companyId=companyId).first()

    @transaction.atomic
    def post(self, request, companyId):
        company = self.get_company(companyId)
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        # only owner or platform admin
        if not (is_owner(request.user, company) or is_platform_admin(request.user)):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Only owner or platform admin can activate setup")

        errors = []

        # basic checks
        if not (company.name and company.email):
            errors.append("Company must have name and contact email")
        if not (company.product_ids and len(company.product_ids) > 0):
            errors.append("At least one module/product must be enabled")
        total_users = len(company.user_list or [])
        if total_users == 0:
            errors.append("At least one user must exist (owner)")

        # subscription existence & license check
        subscription = None
        if company.subscription_ids:
            try:
                subscription_uuid = company.subscription_ids[0]
                subscription = Subscriptions.objects.filter(subscriptionId=subscription_uuid).first()
            except Exception:
                subscription = None

        if not subscription:
            errors.append("A subscription must be created before activation")
        else:
            if (subscription.license_count or 0) < total_users:
                errors.append(f"Subscription licenses ({subscription.license_count}) less than total users ({total_users})")

        if errors:
            return api_response(status_code=status.HTTP_400_BAD_REQUEST, status="error", data={}, error_code="VALIDATION_ERROR", error_message="; ".join(errors))

        try:
            # activate subscription if needed
            if subscription:
                if subscription.is_trial:
                    if not subscription.end_date:
                        subscription.end_date = timezone.now() + timezone.timedelta(days=(subscription.plan.trial_days or 90))
                    subscription.status = Subscriptions.StatusChoices.ACTIVE
                    subscription.save(update_fields=["status", "end_date", "last_updated_date"])
                    company.payment_status = "Pending"
                else:
                    subscription.status = Subscriptions.StatusChoices.ACTIVE
                    subscription.save(update_fields=["status", "last_updated_date"])
                    company.payment_status = "Pending"

            # mark company activated
            company.lifecycle_status = Company.LifecycleStatus.ACTIVE
            company.activated_at = timezone.now()
            company.onboarding_progress = 100
            company.save(update_fields=["lifecycle_status", "activated_at", "onboarding_progress", "last_updated_date", "payment_status"])

            result = {
                "companyId": str(company.companyId),
                "setup_status": "Activated",
                "active_users": total_users,
                "subscription_id": str(subscription.subscriptionId) if subscription else None
            }
            return api_response(status_code=status.HTTP_200_OK, status="success", data=result)
        except Exception as e:
            logger.exception("Activation failed")
            return api_response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, status="error", data={}, error_code="ACTIVATION_FAILED", error_message=str(e))
