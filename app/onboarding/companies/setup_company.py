# app/onboarding/companies/setup_company.py
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.utils.response import api_response
from app.onboarding.companies.serializers import CompanySetupSerializer
from app.onboarding.companies.models import Company
from app.onboarding.users.models import User
from app.products.models import Product
from app.subscriptions.models import SubscriptionPlan, Subscriptions
from app.onboarding.invites.utils import create_invite, send_invite_email
from app.onboarding.invites.serializers import InviteTokenSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Company Setup"],
    summary="Create company (initial setup)",
    description=(
        "Create a Company workspace, add team members (creates invites when needed), "
        "provision modules (products) and optionally create a subscription (trial allowed).\n\n"
        "Authentication: `Authorization: Bearer <access_token>` (SuperAdmin / User creating the workspace)."
    ),
    request=CompanySetupSerializer,
    responses={
        201: OpenApiResponse(description="Company created successfully"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Server error"),
    }
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

                # ------------------------------------------
                # 1️⃣ CREATE COMPANY
                # ------------------------------------------
                company = Company.objects.create(
                    name=company_data.get("name"),
                    description=company_data.get("description", ""),
                    industry=company_data.get("industry", ""),
                    company_size=company_data.get("company_size"),
                    email=company_data.get("email"),
                    phone=company_data.get("phone"),
                    tags=company_data.get("tags", []),
                    discount_percentage=company_data.get("discount_percentage", 0),
                    created_by_user_id=request.user.userId,
                    lifecycle_status=Company.LifecycleStatus.ONBOARDING,
                    onboarding_started_at=timezone.now(),
                    payment_status="Pending",
                )

                # ============================================================
                # 2️⃣ NEW PATCH → Attach creator to company
                # ============================================================
                creator = request.user
                creator.companyId = str(company.companyId)
                creator.role = User.Role.SUPERADMIN
                creator.status = User.Status.ACTIVE
                creator.last_updated_date = timezone.now()
                creator.save(update_fields=["companyId", "role", "status", "last_updated_date"])

                created_user_ids = [str(creator.userId)]
                invite_infos = []
                # ============================================================

                # ------------------------------------------
                # 3️⃣ TEAM MEMBERS
                # ------------------------------------------
                for m in members:
                    email = m["email"].lower().strip()
                    existing = User.objects.filter(email__iexact=email).first()

                    if existing:
                        # existing user
                        if existing.has_usable_password():
                            existing.companyId = str(company.companyId)
                            existing.role = m.get("role", existing.role)
                            existing.status = User.Status.ACTIVE
                            existing.save(update_fields=["companyId", "role", "status", "last_updated_date"])
                            created_user_ids.append(str(existing.userId))

                        else:
                            invite = create_invite(
                                email=email,
                                inviter_user_id=request.user.userId,
                                companyId=company.companyId
                            )
                            meta = send_invite_email(invite)
                            invite_infos.append({
                                "email": email,
                                "invite": InviteTokenSerializer(invite).data,
                                "meta": meta
                            })
                            created_user_ids.append(str(existing.userId))

                    else:
                        # New user — passwordless invite
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
                            companyId=company.companyId
                        )
                        meta = send_invite_email(invite)
                        invite_infos.append({
                            "email": email,
                            "invite": InviteTokenSerializer(invite).data,
                            "meta": meta
                        })
                        created_user_ids.append(str(user.userId))

                # ------------------------------------------
                # 4️⃣ MODULES
                # ------------------------------------------
                product_ids = []
                for mod in modules:
                    code = (mod.get("id") or mod.get("code") or mod.get("title") or "").upper()
                    if not code:
                        continue

                    product, _ = Product.objects.get_or_create(
                        code=code,
                        defaults={
                            "name": mod.get("title", code),
                            "description": mod.get("description", ""),
                            "status": Product.StatusChoices.ACTIVE,
                        }
                    )
                    product_ids.append(str(product.productId))

                # ------------------------------------------
                # 5️⃣ SUBSCRIPTION
                # ------------------------------------------
                subscription_id = None
                if plan_data:
                    plan_name = plan_data.get("id") or plan_data.get("name")
                    plan = SubscriptionPlan.objects.filter(name__iexact=plan_name).first()
                    if not plan:
                        return api_response(
                            status=status.HTTP_400_BAD_REQUEST,
                            status_code="error",
                            data={},
                            error_code="INVALID_PLAN",
                            error_message=f"Plan {plan_name} not found"
                        )

                    is_trial = bool(plan_data.get("trial", False)) and plan.has_trial
                    start = timezone.now()
                    end = start + timezone.timedelta(days=plan.trial_days or 90) if is_trial else None

                    subscription = Subscriptions.objects.create(
                        plan=plan,
                        companyId=company.companyId,
                        userId=request.user.userId,
                        billing_type=plan_data.get("billing_type", Subscriptions.BillingType.MONTHLY),
                        license_count=plan_data.get("license_count", 1),
                        is_trial=is_trial,
                        start_date=start,
                        end_date=end,
                        status=Subscriptions.StatusChoices.ACTIVE if is_trial else Subscriptions.StatusChoices.INACTIVE,
                    )
                    subscription_id = str(subscription.subscriptionId)

                # ------------------------------------------
                # 6️⃣ FINALIZE COMPANY DETAILS
                # ------------------------------------------
                company.user_list = created_user_ids
                company.product_ids = product_ids
                if subscription_id:
                    company.subscription_ids = [subscription_id]
                company.save()

                result = {
                    "companyId": str(company.companyId),
                    "created_user_ids": created_user_ids,
                    "product_ids": product_ids,
                    "subscription_id": subscription_id,
                    "invites": invite_infos,
                }

                return api_response(status_code=status.HTTP_201_CREATED, status="success", data=result)

        except Exception as e:
            logger.exception("Company setup failed")
            return api_response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status_code="error",
                data={},
                error_code="SETUP_FAILED",
                error_message=str(e)
            )
