import logging
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)

from app.utils.response import api_response
from .models import SubscriptionPlan, Subscriptions
from .serializers import SubscriptionPlanSerializer, SubscriptionsSerializer

logger = logging.getLogger(__name__)


# ============================================================
# PERMISSIONS
# ============================================================

class IsPlatformAdmin(permissions.BasePermission):
    """Internal OneIntelligence team only."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", "") == "PlatformAdmin"
        )


class IsSuperAdminOrPlatformAdmin(permissions.BasePermission):
    """Customer owner (SuperAdmin) or internal PlatformAdmin."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return getattr(request.user, "role", "") in ["SuperAdmin", "PlatformAdmin"]


# ============================================================
# SUBSCRIPTION PLANS (Public View, Admin Manage)
# ============================================================

@extend_schema(tags=["Subscription Plans"])
class SubscriptionPlanViewSet(viewsets.ViewSet):
    """
    - Public: list + retrieve plans
    - PlatformAdmin: create/update/delete plans
    """

    def get_permissions(self):
        admin_actions = ["create", "update_plan", "delete_plan"]
        if self.action in admin_actions:
            return [IsPlatformAdmin()]
        return [permissions.AllowAny()]

    # ---------- LIST ----------
    @extend_schema(
        summary="Get all active subscription plans",
        responses={200: SubscriptionPlanSerializer(many=True)},
    )
    def list(self, request):
        plans = SubscriptionPlan.objects.filter(status="Active").order_by("id")
        
        # If no plans in DB, return hardcoded default plans
        if not plans.exists():
            data = self._get_hardcoded_plans()
        else:
            data = SubscriptionPlanSerializer(plans, many=True).data
        
        return api_response(200, "success", data)
    
    def _get_hardcoded_plans(self):
        """Return hardcoded default plans if database is empty."""
        return [
            {
                "id": 1,
                "name": "Pro",
                "multiplier": 1.0,
                "base_prices": {
                    "1": 999,
                    "3": 1999,
                    "5": 2999,
                    "10": 4999,
                    "25": 9999,
                    "50": 17999,
                    "100": 29999
                },
                "features": [
                    "Core workspace modules",
                    "Basic AI assistance",
                    "Email support",
                    "5GB storage per user",
                    "Standard integrations"
                ],
                "has_trial": True,
                "trial_days": 14,
                "global_discount_percentage": 0,
                "status": "Active",
                "created_date": None,
                "last_updated_date": None
            },
            {
                "id": 2,
                "name": "MaxPro",
                "multiplier": 1.5,
                "base_prices": {
                    "1": 1499,
                    "3": 2999,
                    "5": 4499,
                    "10": 7499,
                    "25": 14999,
                    "50": 26999,
                    "100": 44999
                },
                "features": [
                    "All Pro features",
                    "Advanced AI assistance",
                    "Priority support",
                    "25GB storage per user",
                    "Advanced integrations",
                    "Custom workflows",
                    "Advanced analytics"
                ],
                "has_trial": True,
                "trial_days": 30,
                "global_discount_percentage": 0,
                "status": "Active",
                "created_date": None,
                "last_updated_date": None
            },
            {
                "id": 3,
                "name": "Ultra",
                "multiplier": 4.0,
                "base_prices": {
                    "1": 3999,
                    "3": 7999,
                    "5": 11999,
                    "10": 19999,
                    "25": 39999,
                    "50": 71999,
                    "100": 119999
                },
                "features": [
                    "All MaxPro features",
                    "Enterprise AI",
                    "24/7 dedicated support",
                    "Unlimited storage",
                    "All integrations",
                    "Custom development",
                    "Advanced security",
                    "SSO & SAML",
                    "Custom branding",
                    "Dedicated account manager"
                ],
                "has_trial": True,
                "trial_days": 90,
                "global_discount_percentage": 0,
                "status": "Active",
                "created_date": None,
                "last_updated_date": None
            }
        ]

    # ---------- RETRIEVE ----------
    @extend_schema(
        summary="Retrieve a subscription plan",
        responses={200: SubscriptionPlanSerializer},
    )
    def retrieve(self, request, pk=None):
        try:
            plan = SubscriptionPlan.objects.filter(pk=pk).first()
            if plan:
                data = SubscriptionPlanSerializer(plan).data
            else:
                # Check hardcoded plans
                hardcoded_plans = self._get_hardcoded_plans()
                plan_data = next((p for p in hardcoded_plans if p["id"] == int(pk)), None)
                if plan_data:
                    data = plan_data
                else:
                    return api_response(404, "failure", {}, "NOT_FOUND", "Plan not found")
            return api_response(200, "success", data)
        except (ValueError, TypeError):
            return api_response(400, "failure", {}, "INVALID_ID", "Invalid plan ID")

    # ---------- CREATE ----------
    @extend_schema(
        summary="[ADMIN] Create a new subscription plan",
        request=SubscriptionPlanSerializer,
        responses={201: SubscriptionPlanSerializer},
        examples=[
            OpenApiExample(
                "Plan Create Example",
                value={
                    "name": "Pro",
                    "base_prices": {
                        "1": 999,
                        "3": 1999,
                        "5": 2999,
                    },
                    "multiplier": 1.0,
                    "features": ["Feature A", "Feature B"],
                    "has_trial": True,
                    "trial_days": 90,
                    "global_discount_percentage": 10,
                },
            )
        ],
    )
    def create(self, request):
        serializer = SubscriptionPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return api_response(201, "success", SubscriptionPlanSerializer(plan).data)

    # ---------- UPDATE ----------
    @extend_schema(
        summary="[ADMIN] Update a subscription plan",
        request=SubscriptionPlanSerializer,
        responses={200: SubscriptionPlanSerializer},
    )
    @action(detail=True, methods=["put"], url_path="update")
    def update_plan(self, request, pk=None):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        serializer = SubscriptionPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(200, "success", serializer.data)

    # ---------- DELETE ----------
    @extend_schema(
        summary="[ADMIN] Delete subscription plan",
        responses={200: OpenApiResponse(description="Plan deleted")},
    )
    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_plan(self, request, pk=None):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        plan.delete()
        return api_response(200, "success", {"message": "Plan deleted"})


# ============================================================
# COMPANY SUBSCRIPTIONS
# ============================================================

@extend_schema(tags=["Subscriptions"])
class SubscriptionsViewSet(viewsets.ViewSet):
    """
    - SuperAdmin / PlatformAdmin: create, update, cancel subscription
    - Authenticated users: can view `my` subscription
    """

    def get_permissions(self):
        admin_actions = ["create", "update_subscription", "cancel"]
        if self.action in admin_actions:
            return [IsSuperAdminOrPlatformAdmin()]
        return [permissions.IsAuthenticated()]

    # ---------- CREATE ----------
    @extend_schema(
        summary="Create a subscription for a company",
        description=(
            "SuperAdmin or PlatformAdmin can start a subscription.\n"
            "Billing engine inside serializer handles pricing, seat packs, discounts, trials."
        ),
        request=SubscriptionsSerializer,
        responses={201: SubscriptionsSerializer},
        examples=[
            OpenApiExample(
                "Subscription Create Example",
                value={
                    "plan": 1,
                    "companyId": "uuid",
                    "userId": "uuid",
                    "billing_type": "Monthly",
                    "license_count": 5,
                },
            )
        ],
    )
    @transaction.atomic
    def create(self, request):
        # Handle hardcoded plans if plan ID is provided but doesn't exist in DB
        data = request.data.copy()  # Make mutable copy
        plan_id = data.get("plan")
        if plan_id:
            try:
                plan_id = int(plan_id)
                plan_obj = SubscriptionPlan.objects.filter(pk=plan_id).first()
                if not plan_obj:
                    # Check if it's a hardcoded plan ID (1, 2, or 3)
                    hardcoded_plans = SubscriptionPlanViewSet()._get_hardcoded_plans()
                    hardcoded_plan = next((p for p in hardcoded_plans if p["id"] == plan_id), None)
                    if hardcoded_plan:
                        # Create the plan in DB from hardcoded data
                        plan_obj = SubscriptionPlan.objects.create(
                            name=hardcoded_plan["name"],
                            multiplier=hardcoded_plan["multiplier"],
                            base_prices=hardcoded_plan["base_prices"],
                            features=hardcoded_plan["features"],
                            has_trial=hardcoded_plan["has_trial"],
                            trial_days=hardcoded_plan["trial_days"],
                            global_discount_percentage=hardcoded_plan["global_discount_percentage"],
                            status=hardcoded_plan["status"]
                        )
                        # Update data to use the created plan
                        data["plan"] = plan_obj.id
            except (ValueError, TypeError):
                pass  # Let serializer handle validation
        
        serializer = SubscriptionsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        # Auto-set companyId and userId from request.user if not provided
        if not serializer.validated_data.get("companyId") and request.user.company:
            serializer.validated_data["companyId"] = request.user.company.companyId
        if not serializer.validated_data.get("userId"):
            serializer.validated_data["userId"] = request.user.userId
        
        subscription = serializer.save()
        
        # Update company lifecycle status
        if subscription.companyId:
            from app.platform.companies.models import Company
            company = Company.objects.filter(companyId=subscription.companyId).first()
            if company and company.lifecycle_status == "onboarding":
                company.lifecycle_status = "trial" if subscription.is_trial else "active"
                company.plan = subscription.plan.name.lower()
                company.save(update_fields=["lifecycle_status", "plan", "last_updated_date"])
        
        return api_response(201, "success", SubscriptionsSerializer(subscription).data)

    # ---------- GET MY SUBSCRIPTION ----------
    @extend_schema(
        summary="Get the subscription for the logged-in user's company",
        responses={
            200: OpenApiResponse(description="Subscription or null")
        },
    )
    @action(detail=False, methods=["get"], url_path="my")
    def my_subscription(self, request):
        companyId = getattr(request.user, "companyId", None)
        if not companyId:
            return api_response(
                400, "error", error_code="NO_COMPANY", error_message="User not linked to company"
            )

        subscription = (
            Subscriptions.objects.filter(companyId=companyId)
            .order_by("-created_date")
            .first()
        )

        if not subscription:
            return api_response(200, "success", {"subscription": None})

        return api_response(200, "success", SubscriptionsSerializer(subscription).data)

    # ---------- UPDATE SUBSCRIPTION ----------
    @extend_schema(
        summary="Update subscription (plan change, seat count change)",
        request=SubscriptionsSerializer,
        responses={200: SubscriptionsSerializer},
        examples=[
            OpenApiExample(
                "Update Subscription Example",
                value={
                    "plan": 2,
                    "license_count": 10,
                    "billing_type": "Yearly",
                },
            )
        ],
    )
    @action(detail=True, methods=["put"], url_path="update")
    @transaction.atomic
    def update_subscription(self, request, pk=None):
        subscription = get_object_or_404(Subscriptions, pk=pk)
        serializer = SubscriptionsSerializer(
            subscription, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(200, "success", serializer.data)

    # ---------- CANCEL ----------
    @extend_schema(
        summary="Cancel subscription",
        responses={200: OpenApiResponse(description="Subscription cancelled")},
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk=None):
        subscription = get_object_or_404(Subscriptions, pk=pk)
        subscription.status = Subscriptions.StatusChoices.CANCELLED
        subscription.save(update_fields=["status", "last_updated_date"])

        return api_response(200, "success", {"message": "Subscription cancelled"})

    # ---------- GET COMPANY SUBSCRIPTION (for onboarding) ----------
    @extend_schema(
        summary="Get subscription for current user's company",
        description="Returns the active subscription for the authenticated user's company",
    )
    @action(detail=False, methods=["get"], url_path="company")
    def get_company_subscription(self, request):
        """Get subscription for the authenticated user's company."""
        try:
            user = request.user
            if not user.company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User is not associated with a company."
                )

            subscription = (
                Subscriptions.objects
                .filter(companyId=user.company.companyId)
                .order_by("-created_date")
                .first()
            )

            if not subscription:
                return api_response(200, "success", {"subscription": None})

            # Calculate seats used
            from app.platform.accounts.models import User
            seats_used = User.objects.filter(
                company=user.company,
                status=User.Status.ACTIVE
            ).count()

            data = SubscriptionsSerializer(subscription).data
            data["seats_used"] = seats_used
            data["seats_available"] = max(0, subscription.license_count - seats_used)

            return api_response(200, "success", data)

        except Exception as exc:
            logger.exception("Error getting company subscription")
            return api_response(
                500, "failure", {},
                "SERVER_ERROR",
                str(exc)
            )
