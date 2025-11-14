# app/onboarding/companies/update_subscription.py
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.utils.response import api_response
from app.onboarding.companies.models import Company
from app.subscriptions.models import Subscriptions, SubscriptionPlan
from app.onboarding.companies.serializers import CompanySubscriptionUpdateSerializer
from app.onboarding.companies.permissions import is_owner

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Subscription"],
    summary="Update company subscription (owner only)",
    description="Only the company owner (SuperAdmin) may change subscription and license counts.",
    request=CompanySubscriptionUpdateSerializer,
    responses={200: OpenApiResponse(description="Subscription updated")}
)
class CompanySubscriptionUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, companyId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        if not is_owner(request.user, company):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Only owner can update subscription")

        serializer = CompanySubscriptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_data = serializer.validated_data.get("plan")

        sub = None
        if company.subscription_ids:
            try:
                sub_uuid = company.subscription_ids[0]
                sub = Subscriptions.objects.filter(subscriptionId=sub_uuid).first()
            except Exception:
                sub = None

        if plan_data:
            plan_name = plan_data.get("id") or plan_data.get("name")
            plan = SubscriptionPlan.objects.filter(name__iexact=plan_name).first()
            if not plan:
                return api_response(status_code=status.HTTP_400_BAD_REQUEST, status="error", data={}, error_code="INVALID_PLAN", error_message="Plan not found")

            # create if missing
            if not sub:
                is_trial = bool(plan_data.get("trial", False) and plan.has_trial)
                start = timezone.now()
                end = start + timezone.timedelta(days=plan.trial_days or 90) if is_trial else None
                sub = Subscriptions.objects.create(
                    plan=plan,
                    companyId=company.companyId,
                    userId=request.user.userId,
                    billing_type=plan_data.get("billing_type", Subscriptions.BillingType.MONTHLY),
                    license_count=plan_data.get("license_count", 1),
                    is_trial=is_trial,
                    start_date=start,
                    end_date=end,
                    status=Subscriptions.StatusChoices.ACTIVE if is_trial else Subscriptions.StatusChoices.INACTIVE
                )
                company.subscription_ids = [str(sub.subscriptionId)]
                company.save(update_fields=["subscription_ids", "last_updated_date"])
            else:
                # update existing
                sub.plan = plan
                if "billing_type" in plan_data:
                    sub.billing_type = plan_data.get("billing_type")
                if "license_count" in plan_data:
                    sub.license_count = plan_data.get("license_count")
                if "trial" in plan_data and plan.has_trial:
                    sub.is_trial = bool(plan_data.get("trial"))
                    if sub.is_trial and not sub.end_date:
                        sub.end_date = timezone.now() + timezone.timedelta(days=plan.trial_days or 90)
                sub.save()

        return api_response(status_code=status.HTTP_200_OK, status="success", data={"subscription_id": str(sub.subscriptionId) if sub else None})
