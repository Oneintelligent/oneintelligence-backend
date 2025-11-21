"""
Complete Onboarding Flow - One Intelligence
10-step onboarding with annual-only billing, license buckets, and super_plan_access

NO LEGACY SUPPORT - Clean, scalable implementation
"""

import logging
from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from app.platform.accounts.models import User
from app.platform.companies.models import Company
from app.platform.subscriptions.models import SubscriptionPlan, Subscriptions
from app.platform.products.models import ModuleDefinition, CompanyModule
from app.platform.products.defaults import ensure_default_module_definitions
from app.platform.rbac.helpers import assign_role_to_user, assign_super_admin_role
from app.platform.rbac.constants import CustomerRoles, Permissions, Modules
from app.platform.rbac.models import Role, Permission, UserRole, RolePermission, PermissionOverride

logger = logging.getLogger(__name__)


# License bucket discounts
LICENSE_BUCKET_DISCOUNTS = {
    1: 5,      # 1 user gets 5% discount
    3: 10,
    5: 15,
    10: 20,
    20: 25,
    50: 30,
    100: 40,
    1000: 50,  # 1000+ gets 50% discount
}

# Available license buckets
LICENSE_BUCKETS = [1, 3, 5, 10, 20, 50, 100, 1000]

# Annual plan pricing (per user per year in INR)
ANNUAL_PLAN_PRICES = {
    "Pro": 9999,      # No AI
    "Pro Max": 14999,  # AI Recommendations + AI Insights
    "Ultra": 49999,    # Full Conversational AI
}


class OnboardingFlow:
    """
    Complete onboarding flow manager.
    Handles all 10 steps of the onboarding process.
    NO LEGACY SUPPORT - Clean, scalable implementation.
    """
    
    @staticmethod
    def calculate_price(plan_name: str, license_count: int) -> Dict[str, Any]:
        """
        Calculate pricing with bucket discounts.
        
        Formula: final_price = plan_price * users * (1 - discount)
        
        Args:
            plan_name: Plan name (Pro, Pro Max, Ultra)
            license_count: Number of licenses (users)
        
        Returns:
            Dict with base_price, discount_percent, discount_amount, final_price
        """
        # Normalize plan name
        plan_mapping = {
            "Pro": "Pro",
            "MaxPro": "Pro Max",
            "Max Pro": "Pro Max",
            "Pro Max": "Pro Max",
            "Ultra": "Ultra",
        }
        normalized_plan = plan_mapping.get(plan_name, plan_name)
        
        # Get base price per user per year
        base_price_per_user = ANNUAL_PLAN_PRICES.get(normalized_plan, 0)
        if base_price_per_user == 0:
            raise ValueError(f"Invalid plan name: {plan_name}. Must be one of: Pro, Pro Max, Ultra")
        
        # Find appropriate bucket discount
        discount_percent = 0
        # Handle 1000+ case
        if license_count >= 1000:
            discount_percent = LICENSE_BUCKET_DISCOUNTS.get(1000, 50)
        else:
            # Find the largest bucket that license_count is >= to
            for bucket in sorted(LICENSE_BUCKETS, reverse=True):
                if bucket == 1000:
                    continue  # Skip 1000, handled above
                if license_count >= bucket:
                    discount_percent = LICENSE_BUCKET_DISCOUNTS.get(bucket, 0)
                    break
        
        # Calculate prices using formula: final_price = plan_price * users * (1 - discount)
        base_price = base_price_per_user * license_count
        discount_amount = int(base_price * (discount_percent / 100))
        final_price = int(base_price * (1 - discount_percent / 100))
        
        return {
            "base_price": base_price,
            "base_price_per_user": base_price_per_user,
            "license_count": license_count,
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "final_price": final_price,
            "savings": discount_amount,
            "formula": f"₹{base_price_per_user} × {license_count} users × (1 - {discount_percent}%) = ₹{final_price}",
        }
    
    @staticmethod
    @transaction.atomic
    def step1_signup(user_data: Dict[str, Any]) -> User:
        """
        STEP 1: User Signup
        
        Collects: first_name, last_name, email, phone, password
        Creates: User with Super Admin role, temporary workspace (pending_setup)
        """
        from app.platform.accounts.serializers import SignUpSerializer
        
        # Create user
        serializer = SignUpSerializer(data=user_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        logger.info(f"Step 1 completed: User {user.email} signed up")
        return user
    
    @staticmethod
    @transaction.atomic
    def step2_company_setup(user: User, company_data: Dict[str, Any]) -> Company:
        """
        STEP 2: Company Setup
        
        Collects: company_name, industry, country, team_size (optional)
        Actions: Link company → super admin, Move workspace to setup_in_progress
        """
        # Create company
        company = Company.objects.create(
            name=company_data.get("name"),
            email=company_data.get("email", user.email),
            phone=company_data.get("phone", ""),
            country=company_data.get("country", ""),
            industry=company_data.get("industry", ""),
            lifecycle_status="setup_in_progress",
            created_by=user,  # ForeignKey expects User instance, not UUID
        )
        
        # Link user to company
        user.company = company
        user.save(update_fields=["company", "last_updated_date"])
        
        # Assign Super Admin role via RBAC
        assign_super_admin_role(user, company, assigned_by=user)
        
        logger.info(f"Step 2 completed: Company {company.name} created for user {user.email}")
        return company
    
    @staticmethod
    def step3_select_plan() -> list:
        """
        STEP 3: Select Annual Plan
        
        Returns available annual plans with pricing.
        Monthly billing is disabled.
        """
        # Get all active plans from DB
        plans = SubscriptionPlan.objects.filter(status=SubscriptionPlan.StatusChoices.ACTIVE).order_by("id")
        
        # If no plans in DB, or if we don't have both Pro and Pro Max, return default plans
        # This ensures we always have Pro and Pro Max available for onboarding
        plan_names_in_db = set(plans.values_list('name', flat=True))
        has_pro = 'Pro' in plan_names_in_db
        has_pro_max = 'MaxPro' in plan_names_in_db or 'Pro Max' in plan_names_in_db
        
        if not plans.exists() or not (has_pro and has_pro_max):
            return [
                {
                    "id": 1,
                    "name": "Pro",
                    "price_per_user_year": ANNUAL_PLAN_PRICES["Pro"],
                    "description": "No AI",
                    "features": [
                        "Core workspace modules",
                        "Basic features",
                        "Email support",
                    ],
                    "has_trial": True,
                    "trial_days": 90,
                    "trial_requires_card": False,  # No credit card required
                    "status": "active",
                    "recommended": False,
                },
                {
                    "id": 2,
                    "name": "Pro Max",
                    "price_per_user_year": ANNUAL_PLAN_PRICES["Pro Max"],
                    "description": "AI Recommendations + AI Insights",
                    "features": [
                        "All Pro features",
                        "AI Recommendations",
                        "AI Insights",
                        "Priority support",
                    ],
                    "has_trial": True,
                    "trial_days": 90,
                    "trial_requires_card": False,  # No credit card required
                    "status": "active",
                    "recommended": True,  # Pro Max is recommended
                },
                {
                    "id": 3,
                    "name": "Ultra",
                    "price_per_user_year": ANNUAL_PLAN_PRICES["Ultra"],
                    "description": "Full Conversational AI",
                    "features": [
                        "All Pro Max features",
                        "Full Conversational AI",
                        "24/7 support",
                        "Advanced features",
                    ],
                    "has_trial": False,
                    "trial_days": 0,
                    "trial_requires_card": True,
                    "status": "coming_soon",  # Disabled and coming soon
                    "recommended": False,
                },
            ]
        
        # Convert DB plans to response format
        plan_list = []
        has_ultra_in_db = False
        
        for plan in plans:
            # Map DB plan names to display names
            plan_name_map = {
                "Pro": "Pro",
                "MaxPro": "Pro Max",  # Map MaxPro to Pro Max
                "Ultra": "Ultra",
            }
            db_plan_name = plan.name
            display_name = plan_name_map.get(db_plan_name, db_plan_name)
            
            # Track if Ultra exists in DB
            if display_name == "Ultra":
                has_ultra_in_db = True
            
            # Get price - use display name for lookup
            price_per_user = ANNUAL_PLAN_PRICES.get(display_name, 0)
            
            # Determine plan status and trial settings
            if display_name == "Ultra":
                status = "coming_soon"
                has_trial = False
                trial_days = 0
                trial_requires_card = True
                recommended = False
            else:
                # Pro and Pro Max: 90 days free trial, no credit card required
                status = "active"
                has_trial = True
                trial_days = 90
                trial_requires_card = False
                recommended = display_name == "Pro Max"
            
            plan_list.append({
                "id": plan.id,
                "name": display_name,  # Use display name
                "price_per_user_year": price_per_user,
                "description": OnboardingFlow._get_plan_description(display_name),
                "features": plan.features or [],
                "has_trial": has_trial,
                "trial_days": trial_days,
                "trial_requires_card": trial_requires_card,
                "status": status,
                "recommended": recommended,
            })
        
        # Always include Ultra if it's not in the database
        if not has_ultra_in_db:
            plan_list.append({
                "id": 3,
                "name": "Ultra",
                "price_per_user_year": ANNUAL_PLAN_PRICES["Ultra"],
                "description": "Full Conversational AI",
                "features": [
                    "All Pro Max features",
                    "Full Conversational AI",
                    "24/7 support",
                    "Advanced features",
                ],
                "has_trial": False,
                "trial_days": 0,
                "trial_requires_card": True,
                "status": "coming_soon",  # Disabled and coming soon
                "recommended": False,
            })
        
        return plan_list
    
    @staticmethod
    def _get_plan_description(plan_name: str) -> str:
        """Get plan description"""
        descriptions = {
            "Pro": "No AI",
            "Pro Max": "AI Recommendations + AI Insights",
            "Ultra": "Full Conversational AI",
        }
        return descriptions.get(plan_name, "")
    
    @staticmethod
    def step4_choose_license_bucket(plan_name: str, license_count: int) -> Dict[str, Any]:
        """
        STEP 4: Choose License Bucket
        
        Available buckets: 1, 3, 5, 10, 20, 50, 100, 1000+
        Returns pricing breakdown with discounts.
        """
        # Validate license count
        if license_count not in LICENSE_BUCKETS and license_count < 1000:
            # For 1000+, use 1000 bucket discount
            if license_count >= 1000:
                license_count = 1000
            else:
                raise ValueError(f"Invalid license count. Must be one of: {LICENSE_BUCKETS}")
        
        # Calculate pricing
        pricing = OnboardingFlow.calculate_price(plan_name, license_count)
        
        return {
            "plan_name": plan_name,
            "license_count": license_count,
            "available_buckets": LICENSE_BUCKETS,
            "pricing": pricing,
        }
    
    @staticmethod
    @transaction.atomic
    def step5_review_and_payment(
        user: User,
        company: Company,
        plan_id: int,
        license_count: int,
        payment_data: Optional[Dict[str, Any]] = None,
        is_trial: bool = False
    ) -> Dict[str, Any]:
        """
        STEP 5: Review & Payment
        
        Creates subscription, activates workspace, assigns super_plan_access to Super Admin.
        
        For Pro and Pro Max: 90 days free trial (no credit card required)
        For Ultra: Payment required (currently coming soon)
        """
        # Get plan from database
        plan = SubscriptionPlan.objects.filter(pk=plan_id).first()
        
        # If plan doesn't exist in DB, check if it's a hardcoded plan and create it
        if not plan:
            # Check if it's a hardcoded plan ID (1=Pro, 2=Pro Max, 3=Ultra)
            hardcoded_plan_map = {
                1: {
                    "name": "Pro",
                    "multiplier": 1.0,
                    "base_prices": {
                        "1": 9999, "3": 29997, "5": 49995, "10": 99990,
                        "20": 199980, "50": 499950, "100": 999900, "1000": 9999000
                    },
                    "features": ["Core workspace modules", "Basic features", "Email support"],
                    "has_trial": True,
                    "trial_days": 90,
                    "status": SubscriptionPlan.StatusChoices.ACTIVE,
                },
                2: {
                    "name": "MaxPro",  # DB name is MaxPro
                    "multiplier": 1.5,
                    "base_prices": {
                        "1": 14999, "3": 44997, "5": 74995, "10": 149990,
                        "20": 299980, "50": 749950, "100": 1499900, "1000": 14999000
                    },
                    "features": ["All Pro features", "AI Recommendations", "AI Insights", "Priority support"],
                    "has_trial": True,
                    "trial_days": 90,
                    "status": SubscriptionPlan.StatusChoices.ACTIVE,
                },
                3: {
                    "name": "Ultra",
                    "multiplier": 4.0,
                    "base_prices": {
                        "1": 49999, "3": 149997, "5": 249995, "10": 499990,
                        "20": 999980, "50": 2499950, "100": 4999900, "1000": 49999000
                    },
                    "features": ["All Pro Max features", "Full Conversational AI", "24/7 support", "Advanced features"],
                    "has_trial": False,
                    "trial_days": 0,
                    "status": SubscriptionPlan.StatusChoices.INACTIVE,  # Ultra is coming soon
                },
            }
            
            hardcoded_plan_data = hardcoded_plan_map.get(plan_id)
            if hardcoded_plan_data:
                # Create the plan in DB from hardcoded data
                plan = SubscriptionPlan.objects.create(
                    name=hardcoded_plan_data["name"],
                    multiplier=hardcoded_plan_data["multiplier"],
                    base_prices=hardcoded_plan_data["base_prices"],
                    features=hardcoded_plan_data["features"],
                    has_trial=hardcoded_plan_data["has_trial"],
                    trial_days=hardcoded_plan_data["trial_days"],
                    status=hardcoded_plan_data["status"],
                )
                logger.info(f"Created plan {plan.name} (ID: {plan.id}) from hardcoded data for plan_id {plan_id}")
            else:
                raise ValueError(f"Plan with ID {plan_id} not found and is not a valid hardcoded plan")
        
        # Check if Ultra plan (should be disabled)
        plan_name_mapping = {
            "Pro": "Pro",
            "MaxPro": "Pro Max",
            "Max Pro": "Pro Max",
            "Ultra": "Ultra",
        }
        normalized_plan_name = plan_name_mapping.get(plan.name, plan.name)
        
        if normalized_plan_name == "Ultra":
            raise ValueError("Ultra plan is coming soon and not available for purchase yet")
        
        # Determine if this is a trial (Pro and Pro Max get 90 days free trial)
        if normalized_plan_name in ["Pro", "Pro Max"]:
            is_trial = True  # Default to trial for Pro and Pro Max
            trial_days = 90
        else:
            is_trial = False
            trial_days = 0
        
        # Calculate pricing using annual formula
        pricing = OnboardingFlow.calculate_price(normalized_plan_name, license_count)
        
        # For trial, final price is 0
        final_price = 0 if is_trial else pricing["final_price"]
        
        # Ensure license_count is an integer
        license_count = int(license_count)
        
        logger.info(f"Step 5: Processing subscription with license_count: {license_count} (type: {type(license_count)})")
        
        # Check if subscription already exists for this company
        existing_subscription = Subscriptions.objects.filter(
            companyId=company.companyId,
            status=Subscriptions.StatusChoices.ACTIVE
        ).order_by("-created_date").first()
        
        if existing_subscription:
            # Update existing subscription
            logger.info(f"Updating existing subscription {existing_subscription.subscriptionId} with license_count: {license_count}")
            existing_subscription.plan = plan
            existing_subscription.license_count = license_count
            existing_subscription.base_price_per_license = pricing["base_price_per_user"]
            existing_subscription.final_price_per_license = pricing["final_price"] // license_count if license_count > 0 else 0
            existing_subscription.final_total_price = final_price
            existing_subscription.applied_discount = pricing["discount_percent"]
            existing_subscription.is_trial = is_trial
            existing_subscription.trial_text = f"{trial_days} days free trial" if is_trial else None
            existing_subscription.end_date = timezone.now() + timedelta(days=trial_days if is_trial else 365)
            existing_subscription.status = Subscriptions.StatusChoices.ACTIVE
            existing_subscription.save()
            subscription = existing_subscription
            logger.info(f"Subscription updated: license_count={subscription.license_count}, final_total_price={subscription.final_total_price}")
        else:
            # Create new subscription (annual-only)
            logger.info(f"Creating new subscription with license_count: {license_count}")
            subscription = Subscriptions.objects.create(
                plan=plan,
                companyId=company.companyId,
                userId=user.userId,
                billing_type=Subscriptions.BillingType.YEARLY,  # Annual-only
                license_count=license_count,
                base_price_per_license=pricing["base_price_per_user"],
                final_price_per_license=pricing["final_price"] // license_count if license_count > 0 else 0,
                final_total_price=final_price,
                applied_discount=pricing["discount_percent"],
                status=Subscriptions.StatusChoices.ACTIVE,
                is_trial=is_trial,
                trial_text=f"{trial_days} days free trial" if is_trial else None,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=trial_days if is_trial else 365),
            )
            logger.info(f"Subscription created: license_count={subscription.license_count}, final_total_price={subscription.final_total_price}")
        
        # Update company plan but keep in onboarding status until step 10
        # Don't activate workspace yet - that happens at step 10
        company.plan = plan.name.lower()
        # Keep lifecycle_status as "onboarding" to allow remaining steps
        if company.lifecycle_status not in ["onboarding", "setup_in_progress"]:
            company.lifecycle_status = "onboarding"
        company.save(update_fields=["plan", "lifecycle_status", "last_updated_date"])
        
        # Assign super_plan_access permission to Super Admin (automatically)
        OnboardingFlow._assign_super_plan_access(user, company)
        
        logger.info(
            f"Step 5 completed: Subscription created for {company.name}, "
            f"plan: {plan.name}, licenses: {license_count}, price: ₹{pricing['final_price']}"
        )
        
        return {
            "subscription": subscription,
            "pricing": pricing,
            "company": company,
        }
    
    @staticmethod
    def _assign_super_plan_access(user: User, company: Company):
        """Assign super_plan_access permission to Super Admin automatically"""
        try:
            # Get or create the permission
            permission, _ = Permission.objects.get_or_create(
                code=Permissions.SUPER_PLAN_ACCESS.value,
                defaults={
                    "name": "Super Plan Access",
                    "description": "Grants access to Pro and Ultra features WITHOUT additional charge",
                    "category": "special",
                }
            )
            
            # Get Super Admin role
            super_admin_role = Role.objects.filter(
                code=CustomerRoles.SUPER_ADMIN.value,
                is_active=True
            ).first()
            
            if super_admin_role:
                # Assign permission to Super Admin role
                RolePermission.objects.get_or_create(
                    role=super_admin_role,
                    permission=permission,
                    defaults={"is_active": True}
                )
                
                logger.info(f"Assigned super_plan_access to Super Admin role (grants Pro/Ultra features without charge)")
        except Exception as e:
            logger.error(f"Error assigning super_plan_access: {e}")
    
    @staticmethod
    @transaction.atomic
    def step6_add_users(
        company: Company,
        users_data: list,
        assigned_by: User
    ) -> list:
        """
        STEP 6: Add Users
        
        Fields: name, email, role, department, team
        Rules: Must respect purchased user bucket, Status: invited
        """
        # Check license limit
        subscription = Subscriptions.objects.filter(
            companyId=company.companyId,
            status=Subscriptions.StatusChoices.ACTIVE
        ).order_by("-created_date").first()
        
        if not subscription:
            raise ValueError("No active subscription found for company")
        
        # Count existing active users
        existing_users = User.objects.filter(
            company=company,
            status__in=[User.Status.ACTIVE, User.Status.PENDING]
        ).count()
        
        # Check if adding users would exceed license count
        if existing_users + len(users_data) > subscription.license_count:
            raise ValueError(
                f"Cannot add {len(users_data)} users. "
                f"License limit: {subscription.license_count}, "
                f"Current users: {existing_users}, "
                f"Available: {subscription.license_count - existing_users}"
            )
        
        # Create users
        created_users = []
        skipped_users = []
        
        for user_data in users_data:
            email = user_data.get("email", "").strip().lower()
            if not email:
                logger.warning(f"Skipping user with empty email in step6_add_users")
                continue
            
            # Check if user already exists
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                # Check if user belongs to this company
                if existing_user.company == company:
                    logger.info(f"User {email} already exists in company {company.name}, skipping")
                    skipped_users.append({
                        "email": email,
                        "reason": "User already exists in this company"
                    })
                    continue
                else:
                    # User exists but in different company - this is an error
                    raise ValueError(
                        f"User with email {email} already exists in another company. "
                        f"Please use a different email address."
                    )
            
            # Create user invite
            invite_data = {
                "email": email,
                "first_name": user_data.get("first_name", "").strip(),
                "last_name": user_data.get("last_name", "").strip(),
                "role": user_data.get("role", "User"),
            }
            
            try:
                # Create user with PENDING status
                user = User.objects.create(
                    email=invite_data["email"],
                    first_name=invite_data["first_name"],
                    last_name=invite_data["last_name"],
                    company=company,
                    role=invite_data["role"],
                    status=User.Status.PENDING,
                )
                
                # Assign RBAC role
                role_mapping = {
                    "SuperAdmin": CustomerRoles.SUPER_ADMIN.value,
                    "Admin": CustomerRoles.ADMIN.value,
                    "User": CustomerRoles.MEMBER.value,
                }
                role_code = role_mapping.get(invite_data["role"], CustomerRoles.MEMBER.value)
                assign_role_to_user(user, role_code, company=company, assigned_by=assigned_by)
                
                # Create invite token and send email
                from app.platform.invites.models import InviteToken
                from app.platform.invites.utils import send_invite_email
                from django.conf import settings
                
                # Delete old invites for this user
                InviteToken.objects.filter(
                    invited_user_email__iexact=user.email,
                    companyId=company.companyId,
                    used=False
                ).delete()
                
                # Create new invite token
                invite = InviteToken.create_for_user(
                    user=user,
                    inviter_user_id=assigned_by.userId,
                    companyId=company.companyId
                )
                
                # Send invite email
                frontend_url = getattr(settings, 'FRONTEND_BASE', None)
                try:
                    send_invite_email(invite, invite_link_base=frontend_url, company_name=company.name)
                    logger.info(f"Invite email sent to {user.email} for company {company.name}")
                except Exception as email_error:
                    logger.exception(f"Failed to send invite email to {user.email}: {email_error}")
                    # Continue even if email fails - user can still be invited
                
                created_users.append(user)
                logger.info(f"Created user {email} for company {company.name}")
                
            except Exception as e:
                logger.error(f"Failed to create user {email}: {str(e)}")
                # If it's an integrity error (duplicate email), handle it
                if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                    skipped_users.append({
                        "email": email,
                        "reason": "Email already exists"
                    })
                    continue
                # Re-raise other errors
                raise
        
        if skipped_users:
            logger.warning(f"Skipped {len(skipped_users)} users: {skipped_users}")
        
        if not created_users and not skipped_users:
            raise ValueError("No valid users to add. Please check the email addresses.")
        
        logger.info(
            f"Step 6 completed: Added {len(created_users)} users, "
            f"skipped {len(skipped_users)} users to {company.name}"
        )
        return created_users
    
    @staticmethod
    @transaction.atomic
    def step7_assign_special_permission(
        user: User,
        company: Company,
        target_user: User,
        assigned_by: User
    ) -> bool:
        """
        STEP 7: Assign Special Permission (Optional)
        
        Assigns super_plan_access permission to ONE user per company.
        This grants Pro/Ultra features WITHOUT additional charge.
        
        Rules:
        - Only Super Admin can assign this
        - Only ONE user per company can have this permission
        - Grants access to Pro and Ultra features without billing
        - Scalable: Uses database queries to enforce uniqueness
        """
        from app.platform.rbac.utils import is_super_admin
        from app.platform.accounts.models import User
        
        # Verify assigner is Super Admin
        is_admin = is_super_admin(assigned_by, company=company)
        
        # Fallback: Check if user is the company creator (for onboarding)
        is_company_creator = False
        if not is_admin and company:
            # Check if user created the company (first user in company)
            first_user = User.objects.filter(company=company).order_by('created_date').first()
            is_company_creator = (first_user and first_user.userId == assigned_by.userId)
            logger.info(
                f"Step 7 flow: User is company creator: {is_company_creator} "
                f"(first_user: {first_user.email if first_user else 'None'}, "
                f"assigned_by: {assigned_by.email})"
            )
        
        if not is_admin and not is_company_creator:
            logger.warning(
                f"Step 7 flow: User {assigned_by.email} is not Super Admin and not company creator"
            )
            raise ValueError("Only Super Admin can assign super_plan_access")
        
        # Verify target user belongs to the same company
        if target_user.company != company:
            raise ValueError("Target user must belong to the same company")
        
        # Get permission
        permission = Permission.objects.filter(
            code=Permissions.SUPER_PLAN_ACCESS.value,
            is_active=True
        ).first()
        
        if not permission:
            raise ValueError("super_plan_access permission not found")
        
        # CRITICAL: Check if another user already has this permission for this company
        # This ensures only ONE user per company can have super_plan_access
        existing_override = PermissionOverride.objects.filter(
            company=company,
            permission=permission,
            action="grant",
            is_active=True,
            override_type="user",
            module=Modules.AI.value  # Use AI module as placeholder for global permission
        ).exclude(user=target_user).first()
        
        if existing_override:
            existing_user = existing_override.user
            raise ValueError(
                f"super_plan_access is already assigned to {existing_user.email}. "
                f"Only ONE user per company can have this permission. "
                f"Please revoke it from {existing_user.email} first."
            )
        
        # Assign permission override (grants Pro/Ultra features without charge)
        # Note: This does NOT affect billing - user gets features without additional charge
        override, created = PermissionOverride.objects.get_or_create(
            user=target_user,
            company=company,
            permission=permission,
            module=Modules.AI.value,  # Use AI module as placeholder for global permission
            defaults={
                "override_type": "user",
                "action": "grant",
                "is_active": True,
                "created_by": assigned_by,
                "reason": "Super Admin granted super_plan_access - grants Pro/Ultra features without charge",
            }
        )
        
        if not created:
            # Update existing override
            override.action = "grant"
            override.is_active = True
            override.created_by = assigned_by
            override.save()
            logger.info(
                f"Step 7: Updated existing PermissionOverride (id: {override.id}) for {target_user.email}"
            )
        else:
            logger.info(
                f"Step 7: Created new PermissionOverride (id: {override.id}) for {target_user.email}"
            )
        
        # Verify the override was created/updated correctly
        verify_override = PermissionOverride.objects.filter(
            id=override.id,
            is_active=True,
            action="grant",
        ).first()
        
        if not verify_override:
            logger.error(
                f"Step 7 ERROR: PermissionOverride (id: {override.id}) not found after creation/update!"
            )
        else:
            logger.info(
                f"Step 7 verified: PermissionOverride (id: {override.id}) is active with action='grant'"
            )
        
        logger.info(
            f"Step 7 completed: Assigned super_plan_access to {target_user.email} "
            f"by {assigned_by.email} (grants Pro/Ultra features without charge). "
            f"Override ID: {override.id}, Company: {company.name} (ID: {company.companyId})"
        )
        return True
    
    @staticmethod
    @transaction.atomic
    def step7_revoke_special_permission(
        user: User,
        company: Company,
        target_user: User,
        revoked_by: User
    ) -> bool:
        """
        Revoke super_plan_access permission from a user.
        
        Rules:
        - Only Super Admin can revoke
        - Removes Pro/Ultra feature access
        """
        from app.platform.rbac.utils import is_super_admin
        
        # Verify revoker is Super Admin
        if not is_super_admin(revoked_by, company=company):
            raise ValueError("Only Super Admin can revoke super_plan_access")
        
        # Get permission
        permission = Permission.objects.filter(
            code=Permissions.SUPER_PLAN_ACCESS.value,
            is_active=True
        ).first()
        
        if not permission:
            raise ValueError("super_plan_access permission not found")
        
        # Revoke override
        override = PermissionOverride.objects.filter(
            user=target_user,
            company=company,
            permission=permission,
            is_active=True
        ).first()
        
        if override:
            override.is_active = False
            override.created_by = revoked_by
            override.save()
            logger.info(f"Revoked super_plan_access from {target_user.email} by {revoked_by.email}")
            return True
        else:
            raise ValueError(f"super_plan_access not found for user {target_user.email}")
    
    @staticmethod
    @transaction.atomic
    def step8_configure_modules(
        company: Company,
        module_codes: list,
        configured_by: User
    ) -> list:
        """
        STEP 8: Configure Products
        
        Super Admin chooses enabled products.
        Products must reflect plan restrictions for normal users,
        and full access for users with super_plan_access.
        """
        # Get subscription to check plan
        subscription = Subscriptions.objects.filter(
            companyId=company.companyId,
            status=Subscriptions.StatusChoices.ACTIVE
        ).order_by("-created_date").first()
        
        ensure_default_module_definitions()
        
        # Get module definitions
        modules = ModuleDefinition.objects.filter(code__in=module_codes)
        found_codes = set(modules.values_list("code", flat=True))
        missing_codes = set(module_codes) - found_codes
        if missing_codes:
            raise ValueError(f"Modules not found: {', '.join(sorted(missing_codes))}")
        
        # Enable modules
        enabled_modules = []
        for module in modules:
            company_module, created = CompanyModule.objects.get_or_create(
                company_id=company.companyId,
                module=module,
                defaults={"enabled": True}
            )
            if not created and not company_module.enabled:
                company_module.enabled = True
                company_module.save(update_fields=["enabled", "last_updated_date"])
            enabled_modules.append(company_module)
        
        # Update company products list
        company.products = list(found_codes)
        company.save(update_fields=["products", "last_updated_date"])
        
        logger.info(
            f"Step 8 completed: Enabled {len(enabled_modules)} products for {company.name}"
        )
        return enabled_modules
    
    @staticmethod
    @transaction.atomic
    def step9_flac_configuration(
        company: Company,
        flac_config: Dict[str, Any],
        configured_by: User
    ) -> bool:
        """
        STEP 9: Field-Level Access Control (FLAC)
        
        Super Admin configures View/Edit/Hidden per role per module field.
        Users with super_plan_access still follow FLAC for sensitive fields.
        """
        # FLAC configuration stored in company metadata
        if not hasattr(company, 'metadata') or company.metadata is None:
            company.metadata = {}
        
        company.metadata["flac_config"] = flac_config
        company.save(update_fields=["metadata", "last_updated_date"])
        
        logger.info(f"Step 9 completed: FLAC configured for {company.name}")
        return True
    
    @staticmethod
    @transaction.atomic
    def step10_workspace_ready(user: User, company: Company) -> Dict[str, Any]:
        """
        STEP 10: Workspace Ready
        
        Activates the workspace and returns dashboard configuration based on plan and permissions.
        This is the final step that marks onboarding as complete.
        """
        # Get subscription
        subscription = Subscriptions.objects.filter(
            companyId=company.companyId,
            status=Subscriptions.StatusChoices.ACTIVE
        ).order_by("-created_date").first()
        
        plan_name = subscription.plan.name if subscription else "Pro"
        
        # Activate workspace - this is the final step
        # Set lifecycle_status to "active" or "trial" based on subscription
        if subscription and subscription.is_trial:
            company.lifecycle_status = "trial"
        else:
            company.lifecycle_status = "active"
        company.save(update_fields=["lifecycle_status", "last_updated_date"])
        
        # Check if user has super_plan_access
        from app.platform.rbac.utils import get_user_permissions
        user_permissions = get_user_permissions(user, company=company)
        has_super_access = Permissions.SUPER_PLAN_ACCESS.value in user_permissions
        
        # Determine dashboard features
        dashboard_config = {
            "plan": plan_name,
            "has_super_plan_access": has_super_access,
            "features": [],
        }
        
        if has_super_access:
            # User has super_plan_access - gets Pro/Ultra features without charge
            dashboard_config["features"] = [
                "all_plan_features",
                "ai_recommendations",
                "ai_insights",
                "conversational_ai",
                "advanced_analytics",
            ]
        elif plan_name == "Ultra":
            dashboard_config["features"] = [
                "all_plan_features",
                "ai_recommendations",
                "ai_insights",
                "conversational_ai",
            ]
        elif plan_name == "Pro Max":
            dashboard_config["features"] = [
                "core_features",
                "ai_recommendations",
                "ai_insights",
            ]
        else:  # Pro
            dashboard_config["features"] = [
                "core_features",
            ]
        
        logger.info(
            f"Step 10 completed: Workspace activated for {user.email}, "
            f"plan: {plan_name}, super_access: {has_super_access}, "
            f"lifecycle_status: {company.lifecycle_status}"
        )
        
        return {
            "workspace_ready": True,
            "redirect_url": "/workspace/dashboard",
            "dashboard_config": dashboard_config,
        }
