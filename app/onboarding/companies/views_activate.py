import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from app.utils.response import api_response
from app.onboarding.companies.models import Company
from app.subscriptions.models import Subscriptions, SubscriptionPlan
from app.onboarding.users.models import User
from app.onboarding.companies.permissions import is_owner, is_company_admin

logger = logging.getLogger(__name__)


def is_platform_admin(user):
    """Fallback helper: treat explicit role 'PlatformAdmin' as platform admin."""
    try:
        return bool(user and getattr(user, "role", "") == "PlatformAdmin")
    except Exception:
        return False


@extend_schema(
    tags=["Company Setup"],
    summary="Activate company setup (finalize onboarding)",
    description=(
        "Final activation step. Validates company config (info, modules, team, subscription), "
        "ensures license count covers users, activates subscription and marks company active.\n\n"
        "Only the company owner (SuperAdmin) may perform this action. PlatformAdmin may override."
    ),
    responses={
        200: OpenApiResponse(description="Setup activated successfully"),
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Forbidden"),
        404: OpenApiResponse(description="Company not found"),
    },
)
class CompanyActivateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_company(self, companyId):
        return Company.objects.filter(companyId=companyId).first()

    @transaction.atomic
    def post(self, request, companyId):
        """
        POST /api/v1/company/<companyId>/activate-setup/
        Body: {}
        """
        try:
            company = self.get_company(companyId)
            if not company:
                return api_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    data={},
                    error_code="NOT_FOUND",
                    error_message="Company not found",
                )

            current_user = request.user

            # Only owner (SuperAdmin) or platform admin can activate
            if not (is_owner(current_user, company) or is_platform_admin(current_user)):
                return api_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="error",
                    data={},
                    error_code="FORBIDDEN",
                    error_message="Only the company owner or platform admins may activate the setup.",
                )

            # ---------------------------
            # 1) Ensure owner is attached
            # ---------------------------
            owner_id = str(current_user.userId)
            ul = company.user_list or []
            if owner_id not in ul:
                ul.insert(0, owner_id)  # owner as first element
                company.user_list = ul
                # also update the User row if needed
                try:
                    current_user.companyId = str(company.companyId)
                    current_user.role = getattr(current_user, "role", "SuperAdmin") or "SuperAdmin"
                    current_user.status = User.Status.ACTIVE
                    current_user.save(update_fields=["companyId", "role", "status", "last_updated_date"])
                except Exception:
                    logger.exception("Failed to attach owner to company user record")

            # ---------------------------
            # 2) Basic validation checks
            # ---------------------------
            errors = []

            # company basic fields
            if not (company.name and company.email):
                errors.append("Company must have a name and contact email.")

            # modules/products
            product_ids = company.product_ids or []
            if not product_ids:
                errors.append("At least one module/product must be selected.")

            # members
            total_users = len(company.user_list or [])
            if total_users == 0:
                errors.append("At least one user (the owner) must be present in company.user_list.")

            # subscription
            subscription = None
            if company.subscription_ids:
                try:
                    sub_uuid = company.subscription_ids[0]
                    subscription = Subscriptions.objects.filter(subscriptionId=sub_uuid).first()
                except Exception:
                    subscription = None

            if not subscription:
                errors.append("A subscription must be created before activation.")

            # license check
            if subscription:
                license_count = subscription.license_count or 0
                if license_count < total_users:
                    errors.append(
                        f"Subscription license_count ({license_count}) is less than total users ({total_users})."
                    )

            # If any validation errors — return 400
            if errors:
                return api_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    data={},
                    error_code="VALIDATION_ERROR",
                    error_message="; ".join(errors),
                )

            # ---------------------------
            # 3) Activate subscription
            # ---------------------------
            try:
                # If trial, ensure end_date exists and mark as active
                if subscription.is_trial:
                    if not subscription.end_date:
                        # use plan trial_days when available
                        trial_days = getattr(subscription.plan, "trial_days", None) or 90
                        subscription.end_date = timezone.now() + timezone.timedelta(days=trial_days)
                    subscription.status = Subscriptions.StatusChoices.ACTIVE
                    subscription.save(update_fields=["status", "end_date", "last_updated_date"])
                    company.payment_status = "Pending"
                else:
                    # Not a trial: mark active and set payment status to Pending (actual billing outside of this call)
                    subscription.status = Subscriptions.StatusChoices.ACTIVE
                    subscription.save(update_fields=["status", "last_updated_date"])
                    company.payment_status = "Pending"
            except Exception:
                logger.exception("Failed to activate subscription")
                return api_response(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status="error",
                    data={},
                    error_code="SUBSCRIPTION_ACTIVATION_ERROR",
                    error_message="Failed to activate subscription",
                )

            # ---------------------------
            # 4) Mark company active & setup complete
            # ---------------------------
            company.status = Company.StatusChoices.ACTIVE
            # prefer an explicit flag if present, otherwise persist in settings dict
            try:
                if hasattr(company, "is_setup_complete"):
                    company.is_setup_complete = True
                    company.save(update_fields=["status", "is_setup_complete", "last_updated_date", "payment_status", "user_list"])
                else:
                    settings = company.settings or {}
                    settings["setup_complete"] = True
                    company.settings = settings
                    company.save(update_fields=["status", "settings", "last_updated_date", "payment_status", "user_list"])
            except Exception:
                # best-effort save
                company.save(update_fields=["status", "last_updated_date", "payment_status", "user_list"])

            # ---------------------------
            # 5) Return response
            # ---------------------------
            result = {
                "companyId": str(company.companyId),
                "setup_status": "Activated",
                "active_users": total_users,
                "modules": product_ids,
                "subscription": {
                    "subscriptionId": str(subscription.subscriptionId),
                    "plan": subscription.plan.name if subscription.plan else None,
                    "billing_type": subscription.billing_type,
                    "license_count": subscription.license_count,
                    "status": subscription.status,
                    "start_date": subscription.start_date,
                    "end_date": subscription.end_date,
                },
            }

            return api_response(status_code=status.HTTP_200_OK, status="success", data=result)

        except Exception as e:
            logger.exception("Error activating company setup")
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                data={},
                error_code="ACTIVATION_FAILED",
                error_message=str(e),
            )
