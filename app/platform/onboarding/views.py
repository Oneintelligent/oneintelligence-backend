"""
Onboarding API endpoints for managing the complete onboarding flow:
1. Signup → 2. Company → 3. Plan → 4. Modules → 5. Team Members
"""
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema

from app.utils.response import api_response
from app.utils.exception_handler import format_validation_error
from app.platform.accounts.models import User
from app.platform.companies.models import Company
from app.platform.subscriptions.models import Subscriptions, SubscriptionPlan
from app.platform.modules.models import ModuleDefinition, CompanyModule

logger = logging.getLogger(__name__)


@extend_schema(tags=["Onboarding"])
class OnboardingViewSet(viewsets.ViewSet):
    """
    Onboarding flow management:
    - Get onboarding status/progress
    - Track completion of each step
    """
    permission_classes = [permissions.IsAuthenticated]

    def _handle_exception(self, exc, where=""):
        logger.exception(f"{where}: {exc}")
        if isinstance(exc, ValidationError):
            error_message = format_validation_error(exc.detail)
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=error_message,
            )
        error_message = str(exc)
        if hasattr(exc, 'detail'):
            error_message = format_validation_error(exc.detail) if isinstance(exc.detail, (dict, list)) else str(exc.detail)
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=error_message,
        )

    @extend_schema(
        summary="Get onboarding status and progress",
        description="Returns the current onboarding status, completed steps, and next actions",
    )
    @action(detail=False, methods=["get"], url_path="status")
    def get_status(self, request):
        """Get comprehensive onboarding status for the authenticated user."""
        try:
            user = request.user
            company = user.company

            # Step 1: Signup (always complete if user is authenticated)
            signup_complete = True
            signup_data = {
                "completed": signup_complete,
                "user_id": str(user.userId),
                "email": user.email,
                "email_verified": user.email_verified,
            }

            # Step 2: Company
            company_complete = company is not None
            company_data = {
                "completed": company_complete,
                "company_id": str(company.companyId) if company else None,
                "company_name": company.name if company else None,
                "lifecycle_status": company.lifecycle_status if company else "signup",
            }

            # Step 3: Plan/Subscription
            subscription = None
            if company:
                subscription = (
                    Subscriptions.objects
                    .filter(companyId=company.companyId, status=Subscriptions.StatusChoices.ACTIVE)
                    .order_by("-created_date")
                    .first()
                )
            
            plan_complete = subscription is not None
            plan_data = {
                "completed": plan_complete,
                "subscription_id": str(subscription.subscriptionId) if subscription else None,
                "plan_name": subscription.plan.name if subscription else None,
                "license_count": subscription.license_count if subscription else 0,
                "seats_used": self._get_seats_used(company) if company else 0,
                "seats_available": (subscription.license_count - self._get_seats_used(company)) if (subscription and company) else 0,
            }

            # Step 4: Modules
            modules_enabled = []
            if company:
                company_modules = CompanyModule.objects.filter(
                    company_id=company.companyId, enabled=True
                ).select_related("module")
                modules_enabled = [cm.module.code for cm in company_modules]
            
            modules_complete = len(modules_enabled) > 0
            modules_data = {
                "completed": modules_complete,
                "enabled_modules": modules_enabled,
                "count": len(modules_enabled),
            }

            # Step 5: Team Members
            team_members = []
            team_count = 0
            if company:
                team_members = User.objects.filter(
                    company=company, status=User.Status.ACTIVE
                ).values("userId", "email", "first_name", "last_name", "role")
                team_count = team_members.count()
            
            team_complete = team_count > 1  # At least 2 members (creator + 1 invite)
            team_data = {
                "completed": team_complete,
                "total_members": team_count,
                "members": list(team_members),
            }

            # Calculate overall progress
            steps_completed = sum([
                signup_complete,
                company_complete,
                plan_complete,
                modules_complete,
                team_complete,
            ])
            total_steps = 5
            progress_percentage = int((steps_completed / total_steps) * 100)

            # Determine next step
            next_step = None
            if not company_complete:
                next_step = "company"
            elif not plan_complete:
                next_step = "plan"
            elif not modules_complete:
                next_step = "modules"
            elif not team_complete:
                next_step = "team"
            else:
                next_step = "complete"

            response_data = {
                "progress": {
                    "percentage": progress_percentage,
                    "steps_completed": steps_completed,
                    "total_steps": total_steps,
                    "next_step": next_step,
                },
                "steps": {
                    "signup": signup_data,
                    "company": company_data,
                    "plan": plan_data,
                    "modules": modules_data,
                    "team": team_data,
                },
                "can_proceed_to_activation": all([
                    company_complete,
                    plan_complete,
                    modules_complete,
                ]),
            }

            return api_response(200, "success", response_data)

        except Exception as exc:
            return self._handle_exception(exc, "get_status")

    def _get_seats_used(self, company):
        """Get the number of active users (seats used) for a company."""
        if not company:
            return 0
        return User.objects.filter(
            company=company,
            status=User.Status.ACTIVE
        ).count()

