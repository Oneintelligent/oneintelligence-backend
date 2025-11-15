# app/onboarding/companies/views.py

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import CompanySerializer
from app.utils.response import api_response

logger = logging.getLogger(__name__)


@extend_schema(tags=["Company"])
class CompanyAOIViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    # ----------------------------------------
    def _handle_exception(self, exc, where=""):
        logger.exception(f"{where}: {exc}")
        return api_response(500, "failure", {}, "SERVER_ERROR", str(exc))

    # ============================================================
    # CREATE COMPANY
    # ============================================================
    @extend_schema(
        summary="Create new company",
        request=CompanySerializer,
        responses={200: CompanySerializer},
    )
    @action(detail=False, methods=["post"], url_path="create")
    @transaction.atomic
    def create_company(self, request):
        try:
            serializer = CompanySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ⭐ NEW — Extract team members BEFORE create()
            team_members = serializer.validated_data.pop("team_members", [])

            # Create company
            company = Company.objects.create(
                **serializer.validated_data,
                created_by_user=request.user.userId,
            )

            # ⭐ NEW — Process team members: create or update users
            serializer._process_team_members(company, team_members)

            # Link creator to company
            user = request.user
            user.company = company
            user.save(update_fields=["company", "last_updated_date"])

            return api_response(200, "success", CompanySerializer(company).data)

        except Exception as exc:
            return self._handle_exception(exc, "create_company")

    # ============================================================
    # GET COMPANY
    # ============================================================
    @extend_schema(summary="Get company details", responses={200: CompanySerializer})
    @action(detail=True, methods=["get"], url_path="detail")
    def get_company(self, request, pk=None):
        try:
            company = Company.objects.filter(companyId=pk).first()
            if not company:
                return api_response(404, "failure", {}, "NOT_FOUND", "Company not found")

            return api_response(200, "success", CompanySerializer(company).data)
        except Exception as exc:
            return self._handle_exception(exc, "get_company")

    # ============================================================
    # UPDATE COMPANY
    # ============================================================
    @extend_schema(
        summary="Update company details",
        request=CompanySerializer,
        responses={200: CompanySerializer},
    )
    @action(detail=True, methods=["put"], url_path="update")
    @transaction.atomic
    def update_company(self, request, pk=None):
        try:
            company = Company.objects.filter(companyId=pk).first()
            if not company:
                return api_response(404, "failure", {}, "NOT_FOUND", "Company not found")

            serializer = CompanySerializer(company, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # ⭐ NEW — Extract team members BEFORE update
            team_members = serializer.validated_data.pop("team_members", [])

            # Update basic company fields
            for attr, value in serializer.validated_data.items():
                setattr(company, attr, value)
            company.last_updated_date = timezone.now()
            company.save()

            # ⭐ NEW — Add or update team members
            serializer._process_team_members(company, team_members)

            return api_response(200, "success", CompanySerializer(company).data)

        except Exception as exc:
            return self._handle_exception(exc, "update_company")
