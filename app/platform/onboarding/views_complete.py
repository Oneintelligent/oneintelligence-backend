"""
Complete Onboarding Flow API - One Intelligence
10-step onboarding with annual-only billing, license buckets, and super_plan_access
"""

import logging
from django.db import transaction
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from app.utils.response import api_response
from app.utils.exception_handler import format_validation_error
from app.platform.onboarding.flow import OnboardingFlow

logger = logging.getLogger(__name__)


@extend_schema(tags=["Complete Onboarding"])
class CompleteOnboardingViewSet(viewsets.ViewSet):
    """
    Complete 10-step onboarding flow for One Intelligence.
    Annual-only billing, license buckets, super_plan_access.
    
    Some endpoints are public (no auth required), others require authentication.
    """
    
    def get_permissions(self):
        """
        Public endpoints (no auth required):
        - step3-plans: Anyone can view plans
        - step4-license-bucket: Pricing calculation (no user data needed)
        - progress: Can check progress without auth
        
        All other endpoints require authentication.
        """
        public_actions = ['step3_get_plans', 'step4_license_bucket', 'get_progress']
        if self.action in public_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def _handle_exception(self, exc, where=""):
        logger.exception(f"{where}: {exc}")
        from rest_framework.exceptions import ValidationError
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
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=error_message,
        )
    
    # STEP 1: User Signup (handled by accounts/signup endpoint)
    # This is already implemented in app/platform/accounts/views.py
    
    # STEP 2: Company Setup
    @extend_schema(
        summary="Step 2: Company Setup",
        description="Create company and link to super admin"
    )
    @action(detail=False, methods=["post"], url_path="step2-company")
    @transaction.atomic
    def step2_company_setup(self, request):
        """STEP 2: Company Setup"""
        try:
            # Check if user is authenticated (required for this step)
            if not request.user or not request.user.is_authenticated:
                return api_response(
                    401, "failure", {},
                    "AUTH_REQUIRED",
                    "Authentication required. Please complete signup first."
                )
            
            user = request.user
            company_data = request.data
            
            company = OnboardingFlow.step2_company_setup(user, company_data)
            
            return api_response(
                200, "success",
                {
                    "company": {
                        "companyId": str(company.companyId),
                        "name": company.name,
                        "lifecycle_status": company.lifecycle_status,
                    },
                    "step": 2,
                    "next_step": "step3-plan"
                }
            )
        except Exception as exc:
            return self._handle_exception(exc, "step2_company_setup")
    
    # STEP 3: Select Annual Plan
    @extend_schema(
        summary="Step 3: Get Available Annual Plans",
        description="Returns available annual plans (Pro, Pro Max, Ultra)"
    )
    @action(detail=False, methods=["get"], url_path="step3-plans")
    def step3_get_plans(self, request):
        """STEP 3: Get available annual plans (Public endpoint - no auth required)"""
        try:
            plans = OnboardingFlow.step3_select_plan()
            return api_response(200, "success", {
                "plans": plans,
                "billing_type": "annual_only",  # Monthly disabled
                "step": 3,
                "next_step": "step4-license-bucket"
            })
        except Exception as exc:
            return self._handle_exception(exc, "step3_get_plans")
    
    # STEP 4: Choose License Bucket
    @extend_schema(
        summary="Step 4: Calculate License Bucket Pricing",
        description="Calculate pricing with bucket discounts"
    )
    @action(detail=False, methods=["post"], url_path="step4-license-bucket")
    def step4_license_bucket(self, request):
        """STEP 4: Choose license bucket and calculate pricing"""
        try:
            plan_name = request.data.get("plan_name")
            license_count = request.data.get("license_count")
            
            if not plan_name or license_count is None:
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "plan_name and license_count are required"
                )
            
            # Convert to integer if it's a string
            try:
                license_count = int(license_count)
            except (ValueError, TypeError):
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "license_count must be a valid integer"
                )
            
            result = OnboardingFlow.step4_choose_license_bucket(plan_name, license_count)
            
            return api_response(200, "success", {
                **result,
                "step": 4,
                "next_step": "step5-payment"
            })
        except Exception as exc:
            return self._handle_exception(exc, "step4_license_bucket")
    
    # STEP 5: Review & Payment
    @extend_schema(
        summary="Step 5: Review & Payment",
        description="Create subscription, activate workspace, assign super_plan_access"
    )
    @action(detail=False, methods=["post"], url_path="step5-payment")
    @transaction.atomic
    def step5_payment(self, request):
        """STEP 5: Review & Payment"""
        try:
            user = request.user
            company = user.company
            
            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company"
                )
            
            plan_id = request.data.get("plan_id")
            license_count = request.data.get("license_count")
            payment_data = request.data.get("payment", {})  # Payment gateway data
            is_trial = request.data.get("is_trial", True)  # Default to trial for Pro/Pro Max
            
            if not plan_id or license_count is None:
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "plan_id and license_count are required"
                )
            
            # Convert to integer if it's a string
            try:
                plan_id = int(plan_id)
                license_count = int(license_count)
            except (ValueError, TypeError):
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "plan_id and license_count must be valid integers"
                )
            
            # Validate license_count is positive
            if license_count <= 0:
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "license_count must be greater than 0"
                )
            
            # Check if Ultra plan (should be disabled)
            from app.platform.subscriptions.models import SubscriptionPlan
            plan = SubscriptionPlan.objects.filter(pk=plan_id).first()
            if plan and plan.name in ["Ultra"]:
                return api_response(
                    400, "failure", {},
                    "PLAN_UNAVAILABLE",
                    "Ultra plan is coming soon and not available for purchase yet"
                )
            
            result = OnboardingFlow.step5_review_and_payment(
                user, company, plan_id, license_count, payment_data, is_trial
            )
            
            subscription = result["subscription"]
            is_trial = subscription.is_trial
            
            return api_response(200, "success", {
                "subscription": {
                    "subscriptionId": str(subscription.subscriptionId),
                    "plan": subscription.plan.name,
                    "license_count": subscription.license_count,
                    "billing_type": subscription.billing_type,
                    "final_total_price": subscription.final_total_price,
                    "is_trial": is_trial,
                    "trial_days": subscription.plan.trial_days if is_trial else 0,
                    "trial_requires_card": False,  # Pro and Pro Max don't require card
                },
                "pricing": result["pricing"],
                "company": {
                    "companyId": str(result["company"].companyId),
                    "name": result["company"].name,
                    "lifecycle_status": result["company"].lifecycle_status,
                },
                "super_plan_access": "granted",  # Super Admin gets this automatically
                "trial_info": {
                    "is_trial": is_trial,
                    "trial_days": 90 if is_trial else 0,
                    "no_credit_card_required": True if is_trial else False,
                    "message": "90 days free trial - No credit card required" if is_trial else None
                },
                "step": 5,
                "next_step": "step6-add-users"
            })
        except Exception as exc:
            return self._handle_exception(exc, "step5_payment")
    
    # STEP 6: Add Users
    @extend_schema(
        summary="Step 6: Add Users",
        description="Add team members (respects license bucket limit)"
    )
    @action(detail=False, methods=["post"], url_path="step6-add-users")
    @transaction.atomic
    def step6_add_users(self, request):
        """STEP 6: Add Users"""
        try:
            user = request.user
            company = user.company
            
            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company"
                )
            
            users_data = request.data.get("users", [])
            
            if not users_data:
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "users array is required"
                )
            
            if not isinstance(users_data, list):
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "users must be an array"
                )
            
            # Validate each user has required fields
            for idx, user_data in enumerate(users_data):
                if not isinstance(user_data, dict):
                    return api_response(
                        400, "failure", {},
                        "VALIDATION_ERROR",
                        f"User at index {idx} must be an object"
                    )
                email = user_data.get("email", "").strip()
                if not email:
                    return api_response(
                        400, "failure", {},
                        "VALIDATION_ERROR",
                        f"User at index {idx} must have an email address"
                    )
            
            logger.info(
                f"Step 6: Processing {len(users_data)} user(s) for company {company.name} "
                f"(companyId: {company.companyId})"
            )
            
            try:
                created_users = OnboardingFlow.step6_add_users(company, users_data, user)
            except ValueError as ve:
                # Handle validation errors with clear messages
                error_message = str(ve)
                logger.warning(f"Step 6 validation error: {error_message}")
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    error_message
                )
            except Exception as flow_error:
                # Handle other flow errors
                logger.error(f"Step 6 flow error: {flow_error}", exc_info=True)
                return api_response(
                    500, "failure", {},
                    "FLOW_ERROR",
                    f"Failed to add users: {str(flow_error)}"
                )
            
            logger.info(
                f"Step 6: Successfully processed {len(users_data)} user(s), "
                f"created {len(created_users)} new user(s) for company {company.name}"
            )
            
            response_data = {
                "users_added": len(created_users),
                "users": [
                    {
                        "userId": str(u.userId),
                        "email": u.email,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "status": u.status,
                    }
                    for u in created_users
                ],
                "step": 6,
                "next_step": "step7-special-permission"
            }
            
            logger.debug(f"Step 6 response data: {response_data}")
            
            return api_response(200, "success", response_data)
        except Exception as exc:
            logger.exception(f"Step 6 error: {exc}")
            return self._handle_exception(exc, "step6_add_users")
    
    # STEP 7: Assign Special Permission (Optional)
    @extend_schema(
        summary="Step 7: Assign Special Permission",
        description=(
            "Assign super_plan_access to ONE user per company (Super Admin only). "
            "Grants Pro/Ultra features WITHOUT additional charge. "
            "Only ONE user per company can have this permission."
        )
    )
    @action(detail=False, methods=["post"], url_path="step7-special-permission")
    @transaction.atomic
    def step7_special_permission(self, request):
        """
        STEP 7: Assign Special Permission
        
        Rules:
        - Only Super Admin can assign
        - Only ONE user per company can have this
        - Grants Pro/Ultra features without billing
        """
        logger.info(f"Step 7: Received request. User: {request.user.email if request.user else 'None'}")
        try:
            user = request.user
            company = user.company
            logger.info(f"Step 7: User company: {company.name if company else 'None'} (ID: {company.companyId if company else 'None'})")
            
            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company"
                )
            
            # Verify user is Super Admin
            # During onboarding, allow company creator even if role check fails
            from app.platform.rbac.utils import is_super_admin
            is_admin = is_super_admin(user, company=company)
            
            # Fallback: Check if user is the company creator (for onboarding)
            is_company_creator = False
            if not is_admin and company:
                # Check if user created the company (first user in company)
                from app.platform.accounts.models import User
                first_user = User.objects.filter(company=company).order_by('created_date').first()
                is_company_creator = (first_user and first_user.userId == user.userId)
                logger.info(f"Step 7: User is company creator: {is_company_creator} (first_user: {first_user.email if first_user else 'None'})")
            
            logger.info(f"Step 7: Is Super Admin check result: {is_admin}, Is company creator: {is_company_creator}")
            if not is_admin and not is_company_creator:
                logger.warning(f"Step 7: User {user.email} is not Super Admin and not company creator - returning 403")
                return api_response(
                    403, "failure", {},
                    "PERMISSION_DENIED",
                    "Only Super Admin can assign super_plan_access"
                )
            
            target_user_id = request.data.get("user_id")
            logger.info(f"Step 7: Target user_id from request: {target_user_id}")
            
            if not target_user_id:
                logger.warning("Step 7: user_id not provided - returning 400")
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "user_id is required"
                )
            
            from app.platform.accounts.models import User
            target_user = User.objects.filter(userId=target_user_id).first()
            logger.info(f"Step 7: Target user lookup - found: {target_user is not None}, email: {target_user.email if target_user else 'N/A'}")
            
            if not target_user:
                logger.warning(f"Step 7: Target user not found for userId: {target_user_id} - returning 404")
                return api_response(
                    404, "failure", {},
                    "USER_NOT_FOUND",
                    "Target user not found"
                )
            
            # Verify target user belongs to same company
            target_company_id = target_user.company.companyId if target_user.company else None
            logger.info(f"Step 7: Target user company ID: {target_company_id}, Expected: {company.companyId}")
            if target_user.company != company:
                logger.warning(f"Step 7: Company mismatch - returning 400")
                return api_response(
                    400, "failure", {},
                    "INVALID_USER",
                    "Target user must belong to the same company"
                )
            
            logger.info(
                f"Step 7: Assigning special permission to user {target_user.email} "
                f"(userId: {target_user_id}) for company {company.name} (ID: {company.companyId})"
            )
            
            try:
                result = OnboardingFlow.step7_assign_special_permission(
                    user, company, target_user, user
                )
                logger.info(
                    f"Step 7: Flow function returned: {result}"
                )
            except ValueError as ve:
                # Handle validation errors (e.g., permission already assigned)
                logger.warning(f"Step 7 validation error: {str(ve)}")
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    str(ve)
                )
            except Exception as flow_exc:
                logger.error(f"Step 7 flow error: {flow_exc}", exc_info=True)
                raise  # Re-raise to be caught by outer exception handler
            
            logger.info(
                f"Step 7: Successfully assigned special permission. "
                f"Company: {company.name} (ID: {company.companyId}), User: {target_user.email}"
            )
            
            return api_response(200, "success", {
                "message": "super_plan_access granted (Pro/Ultra features without charge)",
                "user": {
                    "userId": str(target_user.userId),
                    "email": target_user.email,
                },
                "note": "Only ONE user per company can have this permission",
                "step": 7,
                "next_step": "step8-modules"
            })
        except ValueError as ve:
            # Handle validation errors (e.g., permission already assigned)
            logger.warning(f"Step 7 ValueError in outer handler: {str(ve)}")
            return api_response(
                400, "failure", {},
                "VALIDATION_ERROR",
                str(ve)
            )
        except Exception as exc:
            logger.exception(f"Step 7 exception in outer handler: {exc}")
            return self._handle_exception(exc, "step7_special_permission")
    
    # Revoke Special Permission
    @extend_schema(
        summary="Revoke Special Permission",
        description="Revoke super_plan_access from a user (Super Admin only)"
    )
    @action(detail=False, methods=["post"], url_path="revoke-special-permission")
    @transaction.atomic
    def revoke_special_permission(self, request):
        """Revoke super_plan_access permission"""
        try:
            user = request.user
            company = user.company
            
            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company"
                )
            
            # Verify user is Super Admin
            from app.platform.rbac.utils import is_super_admin
            if not is_super_admin(user, company=company):
                return api_response(
                    403, "failure", {},
                    "PERMISSION_DENIED",
                    "Only Super Admin can revoke super_plan_access"
                )
            
            target_user_id = request.data.get("user_id")
            
            if not target_user_id:
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "user_id is required"
                )
            
            from app.platform.accounts.models import User
            target_user = User.objects.filter(userId=target_user_id).first()
            
            if not target_user:
                return api_response(
                    404, "failure", {},
                    "USER_NOT_FOUND",
                    "Target user not found"
                )
            
            OnboardingFlow.step7_revoke_special_permission(
                user, company, target_user, user
            )
            
            return api_response(200, "success", {
                "message": "super_plan_access revoked",
                "user": {
                    "userId": str(target_user.userId),
                    "email": target_user.email,
                },
            })
        except ValueError as ve:
            return api_response(
                400, "failure", {},
                "VALIDATION_ERROR",
                str(ve)
            )
        except Exception as exc:
            return self._handle_exception(exc, "revoke_special_permission")
    
    # STEP 8: Configure Products
    @extend_schema(
        summary="Step 8: Configure Products",
        description="Enable products for workspace"
    )
    @action(detail=False, methods=["post"], url_path="step8-modules")  # Keep URL for backward compatibility
    @transaction.atomic
    def step8_modules(self, request):
        """STEP 8: Configure Products"""
        try:
            user = request.user
            company = user.company
            
            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company"
                )
            
            module_codes = request.data.get("module_codes", [])
            
            if not module_codes:
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    "module_codes array is required"
                )
            
            enabled_modules = OnboardingFlow.step8_configure_modules(
                company, module_codes, user
            )
            
            return api_response(200, "success", {
                "products_enabled": len(enabled_modules),
                "products": [em.module.code for em in enabled_modules],
                "modules": [
                    {
                        "code": em.module.code,
                        "name": em.module.name,
                    }
                    for em in enabled_modules
                ],
                "step": 8,
                "next_step": "step9-flac"
            })
        except Exception as exc:
            return self._handle_exception(exc, "step8_modules")
    
    # STEP 9: FLAC Configuration
    @extend_schema(
        summary="Step 9: FLAC Configuration",
        description="Configure field-level access control"
    )
    @action(detail=False, methods=["post"], url_path="step9-flac")
    @transaction.atomic
    def step9_flac(self, request):
        """STEP 9: FLAC Configuration"""
        try:
            user = request.user
            company = user.company
            
            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company"
                )
            
            flac_config = request.data.get("flac_config", {})
            
            OnboardingFlow.step9_flac_configuration(company, flac_config, user)
            
            return api_response(200, "success", {
                "message": "FLAC configured",
                "step": 9,
                "next_step": "step10-workspace-ready"
            })
        except Exception as exc:
            return self._handle_exception(exc, "step9_flac")
    
    # STEP 10: Workspace Ready
    @extend_schema(
        summary="Step 10: Workspace Ready",
        description="Get workspace configuration and redirect info"
    )
    @action(detail=False, methods=["get"], url_path="step10-workspace-ready")
    def step10_workspace_ready(self, request):
        """STEP 10: Workspace Ready"""
        try:
            user = request.user
            company = user.company
            
            if not company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User must belong to a company"
                )
            
            result = OnboardingFlow.step10_workspace_ready(user, company)
            
            return api_response(200, "success", {
                **result,
                "step": 10,
                "onboarding_complete": True
            })
        except Exception as exc:
            return self._handle_exception(exc, "step10_workspace_ready")
    
    # Get Onboarding Progress
    @extend_schema(
        summary="Get Onboarding Progress",
        description="Get current step and progress status"
    )
    @action(detail=False, methods=["get"], url_path="progress")
    def get_progress(self, request):
        """Get onboarding progress (Public endpoint - works with or without auth)"""
        try:
            # Handle unauthenticated users
            if not request.user or not request.user.is_authenticated:
                return api_response(200, "success", {
                    "current_step": 1,
                    "total_steps": 10,
                    "progress_percentage": 10,
                })
            
            user = request.user
            company = getattr(user, 'company', None)
            
            # Determine current step
            current_step = 1
            
            if company:
                current_step = 2
                
                # Check subscription
                from app.platform.subscriptions.models import Subscriptions
                subscription = Subscriptions.objects.filter(
                    companyId=company.companyId,
                    status=Subscriptions.StatusChoices.ACTIVE
                ).first()
                
                if subscription:
                    current_step = 5
                    
                    # Check if users added
                    from app.platform.accounts.models import User
                    user_count = User.objects.filter(
                        company=company,
                        status__in=[User.Status.ACTIVE, User.Status.PENDING]
                    ).count()
                    
                    if user_count > 1:
                        current_step = 6
                    
                    # Check modules
                    from app.platform.products.models import CompanyModule
                    module_count = CompanyModule.objects.filter(
                        company_id=company.companyId,
                        enabled=True
                    ).count()
                    
                    if module_count > 0:
                        current_step = 8
                    
                    # Check FLAC
                    if hasattr(company, 'metadata') and company.metadata and company.metadata.get("flac_config"):
                        current_step = 9
                    
                    # Check if workspace ready
                    if company.lifecycle_status == "active":
                        current_step = 10
            
            return api_response(200, "success", {
                "current_step": current_step,
                "total_steps": 10,
                "progress_percentage": int((current_step / 10) * 100),
            })
        except Exception as exc:
            return self._handle_exception(exc, "get_progress")

