# app/sales/views.py
import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import models

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Account, Lead, Opportunity, Activity
from .serializers import (
    AccountSerializer, LeadSerializer, LeadCreateSerializer,
    OpportunitySerializer, OpportunityCreateSerializer,
    ActivitySerializer, ActivityCreateSerializer
)
from .permissions import (
    IsSalesRecordVisible, can_view_sales_record, can_edit_sales_record, can_delete_sales_record, is_sales_role, HasSalesPermission
)
from app.platform.rbac.mixins import RBACPermissionMixin
from app.platform.rbac.constants import Modules, Permissions
from app.platform.rbac.utils import has_module_permission, is_platform_admin
from .ai_utils import get_recommendation

from app.utils.response import api_response

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helper decorators for consistent schema hiding (similar to AOIViewSet)
# ------------------------------------------------------------------
@extend_schema_view(
    list=extend_schema(exclude=False),
    retrieve=extend_schema(exclude=False),
    create=extend_schema(exclude=False),
    update=extend_schema(exclude=False),
    partial_update=extend_schema(exclude=False),
    destroy=extend_schema(exclude=False),
)
class AccountViewSet(viewsets.ViewSet, RBACPermissionMixin):
    """
    Accounts — standard AOI style ViewSet (list, retrieve, create, update, delete)
    Enterprise-grade RBAC integration
    """
    permission_classes = [IsAuthenticated]
    module = Modules.SALES

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Sales / Accounts"], summary="List accounts (scoped to user)")
    def list(self, request):
        try:
            user = request.user
            
            # Check permission using RBAC
            if not self.check_permission(user, Permissions.VIEW):
                return self.get_permission_denied_response("You don't have permission to view accounts")
            
            # Filter by permissions using RBAC mixin
            qs = Account.objects.filter(company_id=user.company_id)
            qs = self.filter_queryset_by_permissions(qs, user)

            qtext = request.query_params.get("q")
            if qtext:
                qs = qs.filter(Q(name__icontains=qtext) | Q(primary_email__icontains=qtext))

            serializer = AccountSerializer(qs.order_by("name"), many=True)
            return api_response(200, "success", serializer.data)

        except Exception as exc:
            return self._handle_exception(exc, "AccountViewSet.list")

    @extend_schema(tags=["Sales / Accounts"], summary="Retrieve an account")
    def retrieve(self, request, pk=None):
        try:
            account = get_object_or_404(Account, account_id=pk)
            if not self.check_record_access(request.user, account, action="view"):
                return self.get_permission_denied_response("You don't have access to this account")
            serializer = AccountSerializer(account)
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "AccountViewSet.retrieve")

    @extend_schema(tags=["Sales / Accounts"], summary="Create an account", request=AccountSerializer)
    @transaction.atomic
    def create(self, request):
        try:
            # Check permission using RBAC
            if not self.check_permission(request.user, Permissions.CREATE):
                return self.get_permission_denied_response("You don't have permission to create accounts")
            
            serializer = AccountSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # NOTE: Account model does not have `created_by` in your schema shown earlier.
            account = serializer.save(company_id=request.user.company_id)
            return api_response(201, "success", AccountSerializer(account).data)
        except Exception as exc:
            return self._handle_exception(exc, "AccountViewSet.create")

    @extend_schema(tags=["Sales / Accounts"], summary="Update an account", request=AccountSerializer)
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            account = get_object_or_404(Account, account_id=pk)
            if not self.check_record_access(request.user, account, action="edit"):
                return self.get_permission_denied_response("You don't have permission to edit this account")
            serializer = AccountSerializer(account, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "AccountViewSet.update")

    @extend_schema(tags=["Sales / Accounts"], summary="Partially update an account", request=AccountSerializer)
    @transaction.atomic
    def partial_update(self, request, pk=None):
        try:
            account = get_object_or_404(Account, account_id=pk)
            if not self.check_record_access(request.user, account, action="edit"):
                return self.get_permission_denied_response("You don't have permission to edit this account")
            serializer = AccountSerializer(account, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "AccountViewSet.partial_update")

    @extend_schema(tags=["Sales / Accounts"], summary="Delete an account")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            account = get_object_or_404(Account, account_id=pk)
            if not self.check_record_access(request.user, account, action="delete"):
                return self.get_permission_denied_response("You don't have permission to delete this account")
            account.delete()
            return api_response(200, "success", {"message": "Account deleted"})
        except Exception as exc:
            return self._handle_exception(exc, "AccountViewSet.destroy")


# ------------------------------------------------------------------
@extend_schema_view(
    list=extend_schema(exclude=False),
    retrieve=extend_schema(exclude=False),
    create=extend_schema(exclude=False),
    update=extend_schema(exclude=False),
    partial_update=extend_schema(exclude=False),
    destroy=extend_schema(exclude=False),
)
class LeadViewSet(viewsets.ViewSet, RBACPermissionMixin):
    """
    Leads — standardized AOI-style ViewSet
    Enterprise-grade RBAC integration
    """
    permission_classes = [IsAuthenticated, IsSalesRecordVisible]
    module = Modules.SALES

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Sales / Leads"], summary="List leads (scoped to user)")
    def list(self, request):
        try:
            user = request.user
            
            # Check permission using RBAC
            if not self.check_permission(user, Permissions.VIEW):
                return self.get_permission_denied_response("You don't have permission to view leads")
            
            # Filter by permissions using RBAC mixin
            qs = Lead.objects.filter(company_id=user.company_id)
            qs = self.filter_queryset_by_permissions(qs, user)

            status_q = request.query_params.get("status")
            qtext = request.query_params.get("q")
            owner = request.query_params.get("owner")
            if status_q:
                qs = qs.filter(status=status_q)
            if owner:
                qs = qs.filter(owner_id=owner)
            if qtext:
                qs = qs.filter(
                    Q(first_name__icontains=qtext) | Q(last_name__icontains=qtext) |
                    Q(email__icontains=qtext) | Q(organization__icontains=qtext)
                )

            serializer = LeadSerializer(qs.order_by("-updated_at"), many=True)
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.list")

    @extend_schema(tags=["Sales / Leads"], summary="Retrieve a lead")
    def retrieve(self, request, pk=None):
        try:
            lead = get_object_or_404(Lead, lead_id=pk)
            if not self.check_record_access(request.user, lead, action="view"):
                return self.get_permission_denied_response("You don't have access to this lead")
            serializer = LeadSerializer(lead)
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.retrieve")

    @extend_schema(tags=["Sales / Leads"], summary="Create a lead", request=LeadCreateSerializer)
    @transaction.atomic
    def create(self, request):
        try:
            user = request.user
            
            # Check permission using RBAC
            if not self.check_permission(user, Permissions.CREATE):
                return self.get_permission_denied_response("You don't have permission to create leads")
            
            serializer = LeadCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # enforce sensible defaults:
            # if visibility=team but user has no team -> fallback to owner to avoid hidden leads
            vis = serializer.validated_data.get("visibility")
            if vis == "team" and not getattr(user, "team", None):
                serializer.validated_data["visibility"] = "owner"

            # prevent assign to non-sales (optional)
            owner_obj = serializer.validated_data.get("owner", user)
            # Check if owner has sales permissions using RBAC
            if owner_obj:
                from app.platform.rbac.utils import has_module_permission
                from app.platform.rbac.constants import Modules, Permissions
                company = getattr(owner_obj, 'company', None)
                if not has_module_permission(owner_obj, Modules.SALES, Permissions.VIEW, company=company):
                    return api_response(400, "failure", {}, "INVALID_OWNER", "User does not have sales permissions")

            lead = serializer.save(
                company_id=user.company_id,
                owner=owner_obj or user,
                team=getattr(owner_obj, "team", getattr(user, "team", None))
            )
            return api_response(201, "success", LeadSerializer(lead).data)
        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.create")

    @extend_schema(tags=["Sales / Leads"], summary="Update a lead", request=LeadCreateSerializer)
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            lead = get_object_or_404(Lead, lead_id=pk)
            if not can_view_sales_record(request.user, lead):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this lead")

            serializer = LeadCreateSerializer(lead, data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # if owner changed, sync team
            new_owner = getattr(instance, "owner", None)
            if new_owner and getattr(instance, "team", None) != getattr(new_owner, "team", None):
                instance.team = getattr(new_owner, "team", None)
                instance.save(update_fields=["team", "updated_at"])

            return api_response(200, "success", LeadSerializer(instance).data)
        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.update")

    @extend_schema(tags=["Sales / Leads"], summary="Partially update a lead", request=LeadCreateSerializer)
    @transaction.atomic
    def partial_update(self, request, pk=None):
        try:
            lead = get_object_or_404(Lead, lead_id=pk)
            if not can_view_sales_record(request.user, lead):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this lead")

            serializer = LeadCreateSerializer(lead, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # sync team if owner changed
            new_owner = getattr(instance, "owner", None)
            if new_owner and getattr(instance, "team", None) != getattr(new_owner, "team", None):
                instance.team = getattr(new_owner, "team", None)
                instance.save(update_fields=["team", "updated_at"])

            return api_response(200, "success", LeadSerializer(instance).data)
        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.partial_update")

    @extend_schema(tags=["Sales / Leads"], summary="Delete a lead")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            lead = get_object_or_404(Lead, lead_id=pk)
            if not can_view_sales_record(request.user, lead):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this lead")
            lead.delete()
            return api_response(200, "success", {"message": "Lead deleted"})
        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.destroy")

    # ---------------- AI ACTIONS ----------------
    @extend_schema(tags=["Sales / Leads"], summary="On-demand AI lead score")
    @action(detail=True, methods=["post"], url_path="score")
    def score(self, request, pk=None):
        try:
            lead = get_object_or_404(Lead, lead_id=pk)
            if not can_view_sales_record(request.user, lead):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this lead")

            recent_acts = Activity.objects.filter(
                company_id=lead.company_id, entity_type="lead", entity_id=lead.lead_id
            ).order_by("-occurred_at")[:3]

            payload = {
                "lead": {
                    "lead_id": str(lead.lead_id),
                    "first_name": lead.first_name,
                    "last_name": lead.last_name,
                    "email": lead.email,
                    "phone": lead.phone,
                    "status": lead.status,
                    "metadata": lead.metadata,
                },
                "recent_activities": [
                    {"kind": a.kind, "body": a.body, "occurred_at": a.occurred_at.isoformat()}
                    for a in recent_acts
                ],
                "account": {
                    "account_id": str(lead.account.account_id) if lead.account else None,
                    "name": lead.account.name if lead.account else None,
                },
            }

            result = get_recommendation(payload, kind="lead_score")
            if not result:
                return api_response(500, "failure", {}, "AI_ERROR", "AI failed to return result")

            score = result.get("score")
            reasons = result.get("reasons") or []
            if score is not None:
                lead.score = score
                lead.ai_reasons = reasons
                lead.save(update_fields=["score", "ai_reasons", "updated_at"])

            return api_response(200, "success", result)

        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.score")

    @extend_schema(tags=["Sales / Leads"], summary="On-demand AI follow-up suggestion")
    @action(detail=True, methods=["post"], url_path="followup")
    def followup(self, request, pk=None):
        try:
            lead = get_object_or_404(Lead, lead_id=pk)
            if not can_view_sales_record(request.user, lead):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this lead")

            payload = {"lead": {"lead_id": str(lead.lead_id), "email": lead.email, "first_name": lead.first_name, "last_name": lead.last_name, "metadata": lead.metadata}}
            result = get_recommendation(payload, kind="followup")
            if not result:
                return api_response(500, "failure", {}, "AI_ERROR", "AI failed to return result")

            return api_response(200, "success", result)
        except Exception as exc:
            return self._handle_exception(exc, "LeadViewSet.followup")


# ------------------------------------------------------------------
@extend_schema_view(
    list=extend_schema(exclude=False),
    retrieve=extend_schema(exclude=False),
    create=extend_schema(exclude=False),
    update=extend_schema(exclude=False),
    partial_update=extend_schema(exclude=False),
    destroy=extend_schema(exclude=False),
)
class OpportunityViewSet(viewsets.ViewSet):
    """
    Opportunities — AOI-style ViewSet
    """
    permission_classes = [IsAuthenticated, IsSalesRecordVisible]

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Sales / Opportunities"], summary="List opportunities (scoped)")
    def list(self, request):
        try:
            user = request.user
            qs = Opportunity.objects.filter(company_id=user.company_id)
            conditions = Q(owner_id=user.userId) | Q(shared_with__contains=[str(user.userId)])
            if getattr(user, "team_id", None):
                conditions = conditions | Q(team_id=getattr(user, "team_id"))
            if is_sales_role(user):
                conditions = conditions | Q(visibility="company")
            qs = qs.filter(conditions)

            stage = request.query_params.get("stage")
            if stage:
                qs = qs.filter(stage=stage)

            serializer = OpportunitySerializer(qs.order_by("-updated_at"), many=True)
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "OpportunityViewSet.list")

    @extend_schema(tags=["Sales / Opportunities"], summary="Retrieve an opportunity")
    def retrieve(self, request, pk=None):
        try:
            opp = get_object_or_404(Opportunity, opp_id=pk)
            if not can_view_sales_record(request.user, opp):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this opportunity")
            return api_response(200, "success", OpportunitySerializer(opp).data)
        except Exception as exc:
            return self._handle_exception(exc, "OpportunityViewSet.retrieve")

    @extend_schema(tags=["Sales / Opportunities"], summary="Create an opportunity", request=OpportunityCreateSerializer)
    @transaction.atomic
    def create(self, request):
        try:
            user = request.user
            serializer = OpportunityCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            owner_obj = serializer.validated_data.get("owner", user)
            # Check if owner has sales permissions using RBAC
            if owner_obj:
                from app.platform.rbac.utils import has_module_permission
                from app.platform.rbac.constants import Modules, Permissions
                company = getattr(owner_obj, 'company', None)
                if not has_module_permission(owner_obj, Modules.SALES, Permissions.VIEW, company=company):
                    return api_response(400, "failure", {}, "INVALID_OWNER", "User does not have sales permissions")

            opp = serializer.save(company_id=user.company_id, owner=owner_obj or user, team=getattr(owner_obj, "team", getattr(user, "team", None)))
            return api_response(201, "success", OpportunitySerializer(opp).data)
        except Exception as exc:
            return self._handle_exception(exc, "OpportunityViewSet.create")

    @extend_schema(tags=["Sales / Opportunities"], summary="Update an opportunity", request=OpportunityCreateSerializer)
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            opp = get_object_or_404(Opportunity, opp_id=pk)
            if not can_view_sales_record(request.user, opp):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this opportunity")

            serializer = OpportunityCreateSerializer(opp, data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # sync team when owner changed
            new_owner = getattr(instance, "owner", None)
            if new_owner and getattr(instance, "team", None) != getattr(new_owner, "team", None):
                instance.team = getattr(new_owner, "team", None)
                instance.save(update_fields=["team", "updated_at"])

            return api_response(200, "success", OpportunitySerializer(instance).data)
        except Exception as exc:
            return self._handle_exception(exc, "OpportunityViewSet.update")

    @extend_schema(tags=["Sales / Opportunities"], summary="Partially update an opportunity", request=OpportunityCreateSerializer)
    @transaction.atomic
    def partial_update(self, request, pk=None):
        try:
            opp = get_object_or_404(Opportunity, opp_id=pk)
            if not can_view_sales_record(request.user, opp):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this opportunity")

            serializer = OpportunityCreateSerializer(opp, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            new_owner = getattr(instance, "owner", None)
            if new_owner and getattr(instance, "team", None) != getattr(new_owner, "team", None):
                instance.team = getattr(new_owner, "team", None)
                instance.save(update_fields=["team", "updated_at"])

            return api_response(200, "success", OpportunitySerializer(instance).data)
        except Exception as exc:
            return self._handle_exception(exc, "OpportunityViewSet.partial_update")

    # ---------------------------------------------------
    # Convert Opportunity → Account (Closed Won)
    # ---------------------------------------------------
    @extend_schema(
        tags=["Sales / Opportunities"],
        summary="Convert opportunity to Account (Closed Won)"
    )
    @action(detail=True, methods=["post"], url_path="convert")
    @transaction.atomic
    def convert(self, request, pk=None):
        """
        When an opportunity is Closed Won → create an Account (if no true match).
        """
        try:
            opp = get_object_or_404(Opportunity, opp_id=pk)

            # Ensure proper status
            if not opp.stage or opp.stage.lower() != "closed_won":
                return api_response(
                    400,
                    "failure",
                    {},
                    "NOT_WON",
                    "Opportunity must be Closed Won before converting."
                )

            lead = opp.lead
            company_id = opp.company_id

            # 1️⃣ Existing account on the opportunity itself
            if opp.account:
                return api_response(
                    200,
                    "success",
                    {
                        "message": "Opportunity already linked to an account.",
                        "account_id": str(opp.account.account_id),
                        "name": opp.account.name,
                    }
                )

            existing = None
            domain = None

            # 2️⃣ Exact match by email (best-case match)
            if lead and lead.email:
                existing = Account.objects.filter(
                    company_id=company_id,
                    primary_email__iexact=lead.email.strip()
                ).first()

            # 3️⃣ Exact match by name
            if not existing:
                possible_name = None
                if lead and getattr(lead, "organization", None):
                    possible_name = lead.organization
                elif opp.title:
                    possible_name = opp.title
                if possible_name:
                    existing = Account.objects.filter(
                        company_id=company_id,
                        name__iexact=possible_name.strip()
                    ).first()

            # 4️⃣ Domain match — ONLY for business domains
            if not existing and lead and lead.email:
                domain = lead.email.split("@")[-1].lower()
                FREE = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}
                if domain not in FREE:
                    existing = Account.objects.filter(
                        company_id=company_id,
                        website__icontains=domain
                    ).first()

            # If an account truly exists, re-link the opportunity
            if existing:
                opp.account = existing
                opp.save(update_fields=["account"])
                return api_response(
                    200,
                    "success",
                    {
                        "message": "Linked to existing account.",
                        "account_id": str(existing.account_id),
                        "name": existing.name,
                    }
                )

            # 5️⃣ CREATE NEW ACCOUNT (safe and clean)
            new_name = None
            if lead and getattr(lead, "organization", None):
                new_name = lead.organization
            else:
                new_name = opp.title

            new_account = Account.objects.create(
                company_id=company_id,
                owner=opp.owner,
                team=opp.team,
                name=new_name.strip() if new_name else "Unnamed Account",
                website=(domain if domain else None),
                primary_email=(lead.email if lead else None),
                primary_phone=(lead.phone if lead else None),
                visibility="team",
            )

            # Link created account
            opp.account = new_account
            opp.save(update_fields=["account"])

            return api_response(
                200,
                "success",
                {
                    "message": "Account created successfully.",
                    "account_id": str(new_account.account_id),
                    "name": new_account.name,
                }
            )

        except Exception as exc:
            return self._handle_exception(exc, "OpportunityViewSet.convert")

    @extend_schema(tags=["Sales / Opportunities"], summary="Delete an opportunity")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            opp = get_object_or_404(Opportunity, opp_id=pk)
            if not can_view_sales_record(request.user, opp):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this opportunity")
            opp.delete()
            return api_response(200, "success", {"message": "Opportunity deleted"})
        except Exception as exc:
            return self._handle_exception(exc, "OpportunityViewSet.destroy")


# ------------------------------------------------------------------
@extend_schema_view(
    list=extend_schema(exclude=False),
    retrieve=extend_schema(exclude=False),
    create=extend_schema(exclude=False),
    update=extend_schema(exclude=False),
    partial_update=extend_schema(exclude=False),
    destroy=extend_schema(exclude=False),
)
class ActivityViewSet(viewsets.ViewSet):
    """
    Activities — AOI-style ViewSet
    """
    permission_classes = [IsAuthenticated]

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Sales / Activities"], summary="List activities (for entity)")
    def list(self, request):
        try:
            user = request.user
            qs = Activity.objects.filter(company_id=user.company_id)
            entity_type = request.query_params.get("entity_type")
            entity_id = request.query_params.get("entity_id")
            if entity_type and entity_id:
                qs = qs.filter(entity_type=entity_type, entity_id=entity_id)
            serializer = ActivitySerializer(qs.order_by("-occurred_at"), many=True)
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "ActivityViewSet.list")

    @extend_schema(tags=["Sales / Activities"], summary="Retrieve an activity")
    def retrieve(self, request, pk=None):
        try:
            activity = get_object_or_404(Activity, activity_id=pk)
            # activity visibility is tied to parent entity; we assume caller enforces via entity fetch
            serializer = ActivitySerializer(activity)
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "ActivityViewSet.retrieve")

    @extend_schema(tags=["Sales / Activities"], summary="Create an activity", request=ActivityCreateSerializer)
    @transaction.atomic
    def create(self, request):
        try:
            user = request.user
            serializer = ActivityCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            team = getattr(user, "team", None)
            activity = serializer.save(company_id=user.company_id, actor=user, team=team)
            return api_response(201, "success", ActivitySerializer(activity).data)
        except Exception as exc:
            return self._handle_exception(exc, "ActivityViewSet.create")

    @extend_schema(tags=["Sales / Activities"], summary="Update an activity", request=ActivityCreateSerializer)
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            activity = get_object_or_404(Activity, activity_id=pk)
            # optional: validate caller has rights to update (actor or admin)
            serializer = ActivityCreateSerializer(activity, data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            return api_response(200, "success", ActivitySerializer(instance).data)
        except Exception as exc:
            return self._handle_exception(exc, "ActivityViewSet.update")

    @extend_schema(tags=["Sales / Activities"], summary="Partially update an activity", request=ActivityCreateSerializer)
    @transaction.atomic
    def partial_update(self, request, pk=None):
        try:
            activity = get_object_or_404(Activity, activity_id=pk)
            serializer = ActivityCreateSerializer(activity, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            return api_response(200, "success", ActivitySerializer(instance).data)
        except Exception as exc:
            return self._handle_exception(exc, "ActivityViewSet.partial_update")

    @extend_schema(tags=["Sales / Activities"], summary="Delete an activity")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            activity = get_object_or_404(Activity, activity_id=pk)
            activity.delete()
            return api_response(200, "success", {"message": "Activity deleted"})
        except Exception as exc:
            return self._handle_exception(exc, "ActivityViewSet.destroy")


# ------------------------------------------------------------------
# SALES DASHBOARD VIEWSET (AOI-STYLE)
# ------------------------------------------------------------------
@extend_schema_view(
    list=extend_schema(exclude=False),
)
class DashboardViewSet(viewsets.ViewSet):
    """
    Sales Dashboard — aggregated analytics
    """
    permission_classes = [IsAuthenticated]

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Sales / Dashboard"], summary="Get sales dashboard analytics")
    def list(self, request):
        """
        GET /sales/dashboard/
        We use list() to match ViewSet design.
        """
        try:
            user = request.user
            company_id = user.company_id

            # ---------------------------------------------------
            # PIPELINE SUMMARY
            # ---------------------------------------------------
            pipeline_data = (
                Opportunity.objects.filter(company_id=company_id)
                .values("stage")
                .annotate(
                    count=models.Count("opp_id"),
                    amount=models.Sum("amount")
                )
                .order_by("stage")
            )

            # ---------------------------------------------------
            # LEAD STATUS SUMMARY
            # ---------------------------------------------------
            leads = Lead.objects.filter(company_id=company_id)
            lead_stats = {
                "new": leads.filter(status="new").count(),
                "qualified": leads.filter(status="qualified").count(),
                "converted": leads.filter(status="converted").count(),
            }

            # ---------------------------------------------------
            # TOP OPPORTUNITIES
            # ---------------------------------------------------
            top_opps = (
                Opportunity.objects.filter(company_id=company_id)
                .order_by("-amount")[:5]
                .values("title", "amount", "stage")
            )

            # ---------------------------------------------------
            return api_response(
                200,
                "success",
                {
                    "pipeline": list(pipeline_data),
                    "lead_stats": lead_stats,
                    "top_opportunities": list(top_opps),
                },
            )

        except Exception as exc:
            return self._handle_exception(exc, "DashboardViewSet.list")
