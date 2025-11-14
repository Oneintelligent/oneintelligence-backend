# app/onboarding/companies/views.py

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiResponse

from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import CompanySerializer
from app.utils.response import api_response

logger = logging.getLogger(__name__)


@extend_schema(tags=["Company"])
class CompanyAOIViewSet(viewsets.ViewSet):
    """
    Action-oriented ViewSet for Company CRUD operations.
    """
    permission_classes = [permissions.IsAuthenticated]

    # ----------------------------------------
    # Helper
    # ----------------------------------------
    def _handle_exception(self, exc, where=""):
        logger.exception(f"{where}: {exc}")
        return api_response(
            500,
            "failure",
            {},
            "SERVER_ERROR",
            str(exc)
        )

    # ============================================================
    # CREATE COMPANY
    # POST /companies/create/
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

            company = Company.objects.create(
                **serializer.validated_data,
                created_by_user=request.user.userId,
            )

            # Link user automatically
            user = request.user
            user.company = company
            user.save(update_fields=["company", "last_updated_date"])

            return api_response(200, "success", CompanySerializer(company).data)

        except Exception as exc:
            return self._handle_exception(exc, "create_company")

    # ============================================================
    # GET COMPANY
    # GET /companies/<companyId>/detail/
    # ============================================================
    @extend_schema(
        summary="Get company details",
        responses={200: CompanySerializer},
    )
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
    # PUT /companies/<companyId>/update/
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
            serializer.save()

            company.last_updated_date = timezone.now()
            company.save(update_fields=["last_updated_date"])

            return api_response(200, "success", CompanySerializer(company).data)

        except Exception as exc:
            return self._handle_exception(exc, "update_company")
