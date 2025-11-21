"""
Onboarding API endpoints for managing the complete onboarding flow:
1. Signup → 2. Company → 3. Plan → 4. Modules → 5. Team Members

Enterprise-grade onboarding with RBAC integration.
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
from app.platform.products.models import ModuleDefinition, CompanyModule
from app.platform.rbac.utils import get_user_roles, is_super_admin
from app.platform.rbac.helpers import get_user_primary_role
from app.platform.rbac.models import PermissionOverride
from app.platform.rbac.constants import Permissions
from app.platform.consent.utils import has_ai_consent, has_data_storage_consent
from app.platform.consent.models import ConsentType

logger = logging.getLogger(__name__)


@extend_schema(tags=["Onboarding"])
class OnboardingViewSet(viewsets.ViewSet):
    """
    Onboarding flow management with RBAC integration:
    - Get onboarding status/progress
    - Track completion of each step
    - RBAC role information included
    """
    
    def get_permissions(self):
        """
        All onboarding endpoints require authentication.
        Since signup API returns access token, users should be authenticated.
        """
        return [permissions.IsAuthenticated()]

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
        description="Returns the current onboarding status, completed steps, next actions, and RBAC role information",
    )
    @action(detail=False, methods=["get"], url_path="status")
    def get_status(self, request):
        """
        Get comprehensive onboarding status for the authenticated user.
        Includes RBAC role information for all users.
        Requires authentication - signup API returns access token.
        """
        try:
            user = request.user
            company = getattr(user, 'company', None)

            # Step 1: Signup (always complete if user is authenticated)
            signup_complete = True
            
            # Get user's RBAC roles
            user_roles = []
            primary_role = None
            if company:
                roles = get_user_roles(user, company=company)
                user_roles = [{"code": r.code, "display_name": r.display_name} for r in roles]
                primary_role = get_user_primary_role(user, company=company)
            
            # Get consent status
            ai_consent = has_ai_consent(user, company=company) if company else False
            data_storage_consent = has_data_storage_consent(user, company=company) if company else False
            
            signup_data = {
                "completed": signup_complete,
                "user_id": str(user.userId),
                "email": user.email,
                "email_verified": user.email_verified,
                "roles": user_roles,
                "primary_role": {
                    "code": primary_role.code,
                    "display_name": primary_role.display_name
                } if primary_role else None,
                "consents": {
                    "ai_usage": ai_consent,
                    "data_storage": data_storage_consent,
                },
            }

            # Step 2: Company
            company_complete = company is not None
            company_data = {
                "completed": company_complete,
                "company_id": str(company.companyId) if company else None,
                "company_name": company.name if company else None,
                "lifecycle_status": company.lifecycle_status if company else "signup",
                "industry": company.industry if company else None,
                "country": company.country if company else None,
                "company_size": company.company_size if company else None,
                "email": company.email if company else None,
                "phone": company.phone if company else None,
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
            license_count = subscription.license_count if subscription else 0
            
            # Log for debugging
            if subscription:
                logger.info(f"Onboarding status - Subscription found: ID={subscription.subscriptionId}, license_count={license_count}, type={type(license_count)}")
            
            plan_data = {
                "completed": plan_complete,
                "subscription_id": str(subscription.subscriptionId) if subscription else None,
                "plan_name": subscription.plan.name if subscription else None,
                "license_count": license_count,
                "seats_used": self._get_seats_used(company) if company else 0,
                "seats_available": (license_count - self._get_seats_used(company)) if (subscription and company) else 0,
            }

            # Step 4: Products/Modules
            products_enabled = []
            if company:
                company_modules = CompanyModule.objects.filter(
                    company_id=company.companyId, enabled=True
                ).select_related("module")
                products_enabled = [cm.module.code for cm in company_modules]
            
            modules_complete = len(products_enabled) > 0
            modules_data = {
                "completed": modules_complete,
                "enabled_products": products_enabled,
                "products": products_enabled,  # Primary field name
                "count": len(products_enabled),
            }

            # Step 5: Team Members (with RBAC roles)
            team_members = []
            team_count = 0
            if company:
                # Include both ACTIVE and PENDING users (PENDING = invited but not yet activated)
                users = User.objects.filter(
                    company=company, 
                    status__in=[User.Status.ACTIVE, User.Status.PENDING]
                ).select_related("company")
                
                # Get members with RBAC roles
                for u in users:
                    roles = get_user_roles(u, company=company)
                    primary_role = get_user_primary_role(u, company=company)
                    
                    member_data = {
                        "userId": str(u.userId),
                        "email": u.email,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "roles": [{"code": r.code, "display_name": r.display_name} for r in roles],
                        "primary_role": {
                            "code": primary_role.code,
                            "display_name": primary_role.display_name
                        } if primary_role else None,
                    }
                    team_members.append(member_data)
                
                team_count = len(team_members)
            
            team_complete = team_count > 1  # At least 2 members (creator + 1 invite)
            team_data = {
                "completed": team_complete,
                "total_members": team_count,
                "members": team_members,
            }

            # Step 7: Special Permission
            special_permission_data = {
                "completed": False,
                "user": None,
            }
            if company:
                # Query for active permission override with grant action
                override = PermissionOverride.objects.filter(
                    company=company,
                    permission__code=Permissions.SUPER_PLAN_ACCESS.value,
                    is_active=True,
                    override_type="user",
                    action="grant",  # Ensure we only get grants, not revokes
                ).select_related("user", "permission").first()

                if override and override.user:
                    special_permission_data = {
                        "completed": True,
                        "user_id": str(override.user.userId),
                        "user": {
                            "userId": str(override.user.userId),
                            "email": override.user.email,
                            "first_name": override.user.first_name,
                            "last_name": override.user.last_name,
                        },
                        "assigned_at": override.created_date.isoformat() if override.created_date else None,
                    }
                    logger.info(
                        "Onboarding status - super_plan_access assigned to %s (override_id: %s)",
                        override.user.email,
                        override.id if hasattr(override, 'id') else 'unknown'
                    )
                else:
                    # Log when override is not found for debugging
                    all_overrides = PermissionOverride.objects.filter(
                        company=company,
                        permission__code=Permissions.SUPER_PLAN_ACCESS.value,
                    ).select_related("user", "permission")
                    logger.info(
                        "Onboarding status - No active super_plan_access override found for company %s (ID: %s). "
                        "Total overrides for this permission: %d. "
                        "Checking all overrides: %s",
                        company.name,
                        company.companyId,
                        all_overrides.count(),
                        [{"id": o.id, "user": o.user.email if o.user else None, "action": o.action, "is_active": o.is_active} for o in all_overrides[:5]]
                    )

            # Step 9: Access Control (FLAC)
            access_control_data = {
                "completed": False,
                "flac_config": None,
            }
            if company and getattr(company, "metadata", None):
                flac_config = company.metadata.get("flac_config")
                if flac_config:
                    access_control_data["completed"] = True
                    access_control_data["flac_config"] = flac_config
                    logger.info(
                        "Onboarding status - FLAC config detected for company %s",
                        company.name,
                    )

            # Step 10: Workspace readiness snapshot
            workspace_ready = company and company.lifecycle_status in ["trial", "active"]
            workspace_data = {
                "completed": bool(workspace_ready),
                "lifecycle_status": company.lifecycle_status if company else None,
                "can_activate": plan_complete and modules_complete,
                "products_enabled": company.products if company else [],
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
                    "special_permission": special_permission_data,
                    "access_control": access_control_data,
                    "workspace": workspace_data,
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

    @extend_schema(
        summary="Complete onboarding and activate workspace",
        description="Marks onboarding as complete and activates the workspace",
    )
    @action(detail=False, methods=["post"], url_path="complete")
    @transaction.atomic
    def complete_onboarding(self, request):
        """
        Complete onboarding and activate workspace.
        Requires Super Admin role.
        """
        try:
            user = request.user
            company = user.company

            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company to complete onboarding"
                )

            # Check if user is Super Admin
            if not is_super_admin(user, company=company):
                return api_response(
                    403, "failure", {},
                    "PERMISSION_DENIED",
                    "Only Super Admin can complete onboarding"
                )

            # Check if all required steps are complete
            subscription = (
                Subscriptions.objects
                .filter(companyId=company.companyId, status=Subscriptions.StatusChoices.ACTIVE)
                .order_by("-created_date")
                .first()
            )

            if not subscription:
                return api_response(
                    400, "failure", {},
                    "NO_SUBSCRIPTION",
                    "Subscription is required to activate workspace"
                )

            modules_count = CompanyModule.objects.filter(
                company_id=company.companyId, enabled=True
            ).count()

            if modules_count == 0:
                return api_response(
                    400, "failure", {},
                    "NO_MODULES",
                    "At least one module must be enabled to activate workspace"
                )

            # Activate company
            company.lifecycle_status = "active"
            company.save(update_fields=["lifecycle_status", "last_updated_date"])

            logger.info(f"Onboarding completed for company {company.companyId} by user {user.email}")

            return api_response(
                200, "success",
                {
                    "message": "Onboarding completed successfully",
                    "company": {
                        "companyId": str(company.companyId),
                        "name": company.name,
                        "lifecycle_status": company.lifecycle_status,
                    }
                }
            )

        except Exception as exc:
            return self._handle_exception(exc, "complete_onboarding")

    def _get_seats_used(self, company):
        """Get the number of active users (seats used) for a company."""
        if not company:
            return 0
        return User.objects.filter(
            company=company,
            status=User.Status.ACTIVE
        ).count()
