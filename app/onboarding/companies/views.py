# app/onboarding/companies/views.py

import logging
from django.db import transaction
from django.utils import timezone

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
)

from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import (
    CompanySetupSerializer,
    CompanySettingsSerializer,
    TeamMemberSerializer,
    CompanyDiscountSerializer,
)
from app.onboarding.users.models import User
from app.products.models import Product
from app.subscriptions.models import SubscriptionPlan, Subscriptions
from app.onboarding.invites.utils import create_invite, send_invite_email
from app.onboarding.invites.serializers import InviteTokenSerializer
from app.onboarding.invites.models import InviteToken

from app.utils.response import api_response
from app.onboarding.companies.permissions import (
    is_owner,
    is_company_admin,
    is_platform_admin,
)

logger = logging.getLogger(__name__)


# ============================================================
# COMPANY SETUP (One-Time)
# ============================================================

@extend_schema(
    tags=["Company Setup"],
    summary="Create company (initial setup)",
    description="Creates a company, adds team members, assigns modules, and initializes a subscription.",
    request=CompanySetupSerializer,
    responses={
        201: OpenApiResponse(
            description="Company successfully created",
            examples=[
                OpenApiExample(
                    "Success Example",
                    value={
                        "statusCode": 201,
                        "status": "success",
                        "data": {
                            "companyId": "uuid",
                            "created_user_ids": ["uuid"],
                            "product_ids": ["uuid"],
                            "subscription_id": "uuid",
                            "invites": [
                                {
                                    "email": "member@example.com",
                                    "invite": {"token": "abc123"},
                                }
                            ],
                        },
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Internal server error"),
    },
)
class CompanySetupAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CompanySetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        company_data = payload.get("company", {})
        members = payload.get("members", [])
        modules = payload.get("modules", [])
        plan_data = payload.get("plan")

        try:
            with transaction.atomic():
                # -------------------------------------------------------------
                # CREATE COMPANY
                # -------------------------------------------------------------
                company = Company.objects.create(
                    name=company_data["name"],
                    description=company_data.get("description", ""),
                    industry=company_data.get("industry", ""),
                    company_size=company_data.get("company_size"),
                    email=company_data.get("email"),
                    phone=company_data.get("phone"),
                    tags=company_data.get("tags", []),
                    discount_percentage=company_data.get("discount_percentage", 0),
                    created_by_user_id=request.user.userId,
                    status=Company.StatusChoices.ACTIVE,
                )

                created_user_ids = []
                invite_infos = []

                # -------------------------------------------------------------
                # TEAM MEMBERS
                # -------------------------------------------------------------
                for m in members:
                    email = m["email"].lower().strip()
                    existing = User.objects.filter(email__iexact=email).first()

                    # Case: user exists
                    if existing:
                        if existing.has_usable_password():
                            existing.companyId = str(company.companyId)
                            existing.role = m.get("role", existing.role)
                            existing.status = User.Status.ACTIVE
                            existing.save()
                            created_user_ids.append(str(existing.userId))
                        else:
                            invite = create_invite(
                                email=email,
                                inviter_user_id=request.user.userId,
                                companyId=company.companyId,
                            )
                            meta = send_invite_email(invite)
                            invite_infos.append({
                                "email": email,
                                "invite": InviteTokenSerializer(invite).data,
                                "meta": meta,
                            })
                            created_user_ids.append(str(existing.userId))

                    # Case: new user
                    else:
                        user = User.objects.create(
                            email=email,
                            first_name=m.get("first_name", ""),
                            last_name=m.get("last_name", ""),
                            role=m.get("role", User.Role.USER),
                            companyId=str(company.companyId),
                            status=User.Status.INACTIVE,
                        )
                        user.set_unusable_password()
                        user.save()

                        invite = create_invite(
                            email=email,
                            inviter_user_id=request.user.userId,
                            companyId=company.companyId,
                        )
                        meta = send_invite_email(invite)

                        invite_infos.append({
                            "email": email,
                            "invite": InviteTokenSerializer(invite).data,
                            "meta": meta,
                        })

                        created_user_ids.append(str(user.userId))

                # -------------------------------------------------------------
                # MODULES → PRODUCTS
                # -------------------------------------------------------------
                product_ids = []
                for mod in modules:
                    code = (
                        mod.get("id")
                        or mod.get("code")
                        or mod.get("title")
                    ).upper()

                    product, _ = Product.objects.get_or_create(
                        code=code,
                        defaults={
                            "name": mod.get("title", code),
                            "description": mod.get("description", ""),
                            "status": Product.StatusChoices.ACTIVE,
                        },
                    )
                    product_ids.append(str(product.productId))

                # -------------------------------------------------------------
                # SUBSCRIPTION
                # -------------------------------------------------------------
                subscription_id = None
                if plan_data:
                    plan_name = plan_data.get("id") or plan_data.get("name")
                    plan = SubscriptionPlan.objects.filter(
                        name__iexact=plan_name
                    ).first()

                    if not plan:
                        return api_response(
                            400,
                            "error",
                            error_code="INVALID_PLAN",
                            error_message=f"Plan '{plan_name}' does not exist.",
                        )

                    is_trial = (
                        bool(plan_data.get("trial", False)) and plan.has_trial
                    )

                    start = timezone.now()
                    end = (
                        start + timezone.timedelta(days=plan.trial_days)
                        if is_trial
                        else None
                    )

                    subscription = Subscriptions.objects.create(
                        plan=plan,
                        companyId=company.companyId,
                        userId=request.user.userId,
                        billing_type=plan_data.get("billing_type", Subscriptions.BillingType.MONTHLY),
                        license_count=plan_data.get("license_count", 1),
                        is_trial=is_trial,
                        start_date=start,
                        end_date=end,
                        status=(
                            Subscriptions.StatusChoices.ACTIVE
                            if is_trial
                            else Subscriptions.StatusChoices.INACTIVE
                        ),
                    )

                    subscription_id = str(subscription.subscriptionId)

                # -------------------------------------------------------------
                # UPDATE COMPANY
                # -------------------------------------------------------------
                company.user_list = created_user_ids
                company.product_ids = product_ids
                if subscription_id:
                    company.subscription_ids = [subscription_id]
                company.payment_status = "Pending"
                company.save()

                # -------------------------------------------------------------
                # RESPONSE
                # -------------------------------------------------------------
                result = {
                    "companyId": str(company.companyId),
                    "created_user_ids": created_user_ids,
                    "product_ids": product_ids,
                    "subscription_id": subscription_id,
                    "invites": invite_infos,
                }

                return api_response(201, "success", result)

        except Exception as e:
            logger.exception("Company setup failed")
            return api_response(
                500,
                "error",
                error_code="SETUP_FAILED",
                error_message=str(e),
            )


# ============================================================
# COMPANY SETTINGS (GET / PUT)
# ============================================================

@extend_schema(
    tags=["Company Settings"],
    summary="Get or update company settings",
)
class CompanySettingsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_company(self, companyId):
        return Company.objects.filter(companyId=companyId).first()

    # ---------- GET ----------
    @extend_schema(
        responses={200: CompanySettingsSerializer},
    )
    def get(self, request, companyId):
        company = self.get_company(companyId)
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        return api_response(200, "success", CompanySettingsSerializer(company).data)

    # ---------- PUT ----------
    @extend_schema(
        request=CompanySettingsSerializer,
        responses={200: CompanySettingsSerializer, 403: OpenApiResponse(description="Forbidden")},
    )
    @transaction.atomic
    def put(self, request, companyId):
        company = self.get_company(companyId)
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Not allowed to update settings")

        serializer = CompanySettingsSerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if "discount_percentage" in serializer.validated_data and not is_owner(request.user, company):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Only owner can modify discount")

        serializer.save()
        return api_response(200, "success", serializer.data)


# ============================================================
# TEAM MEMBER MANAGEMENT (Add / Update / Delete)
# ============================================================

@extend_schema(
    tags=["Team"],
    summary="Manage team members for a company",
)
class TeamMemberAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # ---------- ADD MEMBER ----------
    @extend_schema(
        request=TeamMemberSerializer,
        responses={201: OpenApiResponse(description="User added")},
    )
    @transaction.atomic
    def post(self, request, companyId):
        serializer = TeamMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Not allowed to add members")

        email = data["email"].lower().strip()
        existing = User.objects.filter(email__iexact=email).first()
        invite_meta = None

        # Existing user
        if existing:
            if existing.has_usable_password():
                existing.companyId = str(company.companyId)
                existing.role = data.get("role", existing.role)
                existing.status = User.Status.ACTIVE
                existing.save()
                user_id = str(existing.userId)
            else:
                invite = create_invite(email=email, inviter_user_id=request.user.userId, companyId=company.companyId)
                invite_meta = send_invite_email(invite)
                user_id = str(existing.userId)

        # New user
        else:
            user = User.objects.create(
                email=email,
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                role=data.get("role", User.Role.USER),
                companyId=str(company.companyId),
                status=User.Status.INACTIVE,
            )
            user.set_unusable_password()
            user.save()

            invite = create_invite(email=email, inviter_user_id=request.user.userId, companyId=company.companyId)
            invite_meta = send_invite_email(invite)
            user_id = str(user.userId)

        # Update company user list
        ul = company.user_list or []
        if user_id not in ul:
            ul.append(user_id)
            company.user_list = ul
            company.save()

        return api_response(201, "success", {"userId": user_id, "invite": invite_meta or {}})

    # ---------- UPDATE MEMBER ----------
    @extend_schema(
        request=TeamMemberSerializer,
        responses={200: OpenApiResponse(description="User updated")},
    )
    @transaction.atomic
    def put(self, request, companyId, userId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Not allowed to update members")

        user = User.objects.filter(userId=userId).first()
        if not user or str(user.companyId) != str(company.companyId):
            return api_response(404, "error", error_code="NOT_FOUND", error_message="User not found")

        allowed_fields = ["first_name", "last_name", "role", "status", "phone", "profile_picture_url"]
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])

        user.save()
        return api_response(200, "success", {"updated": True})

    # ---------- DELETE MEMBER ----------
    @extend_schema(
        responses={200: OpenApiResponse(description="User removed")},
    )
    @transaction.atomic
    def delete(self, request, companyId, userId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Not allowed to remove members")

        user = User.objects.filter(userId=userId).first()
        if not user:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="User not found")

        # Remove from user + company user_list
        if str(user.companyId) == str(company.companyId):
            user.companyId = None
            user.save()

        ul = company.user_list or []
        if str(userId) in ul:
            ul.remove(str(userId))
            company.user_list = ul
            company.save()

        return api_response(200, "success", {"removed": True})


# ============================================================
# PRODUCTS / MODULES UPDATE
# ============================================================

@extend_schema(
    tags=["Products"],
    summary="Update the list of modules/products used by a company",
    request={
        "type": "object",
        "properties": {
            "modules": {
                "type": "array",
                "items": {"type": "object"},
            }
        },
    },
    responses={200: OpenApiResponse(description="Modules updated")},
)
class CompanyProductsUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, companyId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Not allowed to update modules")

        modules = request.data.get("modules", [])
        product_ids = []

        for mod in modules:
            code = (
                mod.get("id")
                or mod.get("code")
                or mod.get("title")
            ).upper()

            product, _ = Product.objects.update_or_create(
                code=code,
                defaults={
                    "name": mod.get("title", code),
                    "description": mod.get("description", ""),
                    "status": Product.StatusChoices.ACTIVE,
                },
            )
            product_ids.append(str(product.productId))

        company.product_ids = product_ids
        company.save()
        return api_response(200, "success", {"product_ids": product_ids})


# ============================================================
# SUBSCRIPTION UPDATE (OWNER ONLY)
# ============================================================

@extend_schema(
    tags=["Subscription"],
    summary="Update subscription (only company owner)",
    request={
        "type": "object",
        "properties": {
            "plan": {"type": "object"},
        },
    },
    responses={200: OpenApiResponse(description="Subscription updated")},
)
class CompanySubscriptionUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, companyId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        if not is_owner(request.user, company):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Only owner can update subscription")

        plan_data = request.data.get("plan")
        subscription_obj = None

        if company.subscription_ids:
            subscription_obj = Subscriptions.objects.filter(
                subscriptionId=company.subscription_ids[0]
            ).first()

        if plan_data:
            plan_name = plan_data.get("id") or plan_data.get("name")
            plan = SubscriptionPlan.objects.filter(name__iexact=plan_name).first()

            if not plan:
                return api_response(400, "error", error_code="INVALID_PLAN", error_message="Plan not found")

            # Create new subscription if needed
            if not subscription_obj:
                subscription_obj = Subscriptions.objects.create(
                    plan=plan,
                    companyId=company.companyId,
                    userId=request.user.userId,
                    billing_type=plan_data.get("billing_type", Subscriptions.BillingType.MONTHLY),
                    license_count=plan_data.get("license_count", 1),
                    is_trial=bool(plan_data.get("trial", False) and plan.has_trial),
                )
                company.subscription_ids = [str(subscription_obj.subscriptionId)]
                company.save()
            else:
                # Update existing
                subscription_obj.plan = plan
                if "billing_type" in plan_data:
                    subscription_obj.billing_type = plan_data.get("billing_type")
                if "license_count" in plan_data:
                    subscription_obj.license_count = plan_data.get("license_count")

                # Handle trial restart
                if "trial" in plan_data and plan.has_trial:
                    subscription_obj.is_trial = bool(plan_data.get("trial"))
                    if subscription_obj.is_trial and not subscription_obj.end_date:
                        subscription_obj.end_date = timezone.now() + timezone.timedelta(days=plan.trial_days)

                subscription_obj.save()

        return api_response(
            200,
            "success",
            {"subscription_id": str(subscription_obj.subscriptionId) if subscription_obj else None},
        )


# ============================================================
# DISCOUNT UPDATE (PlatformAdmin Only)
# ============================================================

@extend_schema(
    tags=["Company Admin"],
    summary="Update company discount (PlatformAdmin only)",
    description="Only internal OneIntelligence platform admins may update company-level discounts.",
    request=CompanyDiscountSerializer,
    responses={
        200: OpenApiResponse(description="Discount updated"),
        403: OpenApiResponse(description="Forbidden"),
        404: OpenApiResponse(description="Company not found"),
    },
)
class CompanyDiscountUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, companyId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(404, "error", error_code="NOT_FOUND", error_message="Company not found")

        if not is_platform_admin(request.user):
            return api_response(403, "error", error_code="FORBIDDEN", error_message="Only platform admins can update discounts")

        serializer = CompanyDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company.discount_percentage = serializer.validated_data["discount_percentage"]
        company.save()

        return api_response(
            200,
            "success",
            {
                "companyId": str(company.companyId),
                "discount_percentage": company.discount_percentage,
                "updated_by": request.user.email,
            },
        )
