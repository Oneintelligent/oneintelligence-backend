# app/onboarding/companies/views.py

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ValidationError as SerializerValidationError
from drf_spectacular.utils import extend_schema

from app.platform.companies.models import Company
from app.platform.companies.serializers import CompanySerializer
from app.utils.response import api_response
from app.utils.exception_handler import format_validation_error
from app.platform.accounts.models import User

logger = logging.getLogger(__name__)


@extend_schema(tags=["Company"])
class CompanyAOIViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    # -------------------------------------------------------
    def _handle_exception(self, exc, where=""):
        logger.exception(f"{where}: {exc}")
        
        # Handle validation errors with readable messages
        if isinstance(exc, (ValidationError, SerializerValidationError)):
            error_message = format_validation_error(exc.detail)
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=error_message,
            )
        
        # Handle other exceptions
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

    # =======================================================
    # CREATE COMPANY
    # =======================================================
    @extend_schema(
        summary="Create a new company",
        request=CompanySerializer,
        responses={200: CompanySerializer},
    )
    @action(detail=False, methods=["post"], url_path="create")
    @transaction.atomic
    def create_company(self, request):
        try:
            user = request.user

            # security: user cannot create another company if already in one
            if user.company:
                return api_response(
                    400,
                    "failure",
                    {},
                    "ALREADY_IN_COMPANY",
                    "You already belong to a company.",
                )

            serializer = CompanySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # let serializer handle creation + team members
            company = serializer.save(created_by=request.user)

            # Set lifecycle status to onboarding if not already set
            if not company.lifecycle_status or company.lifecycle_status == "signup":
                company.lifecycle_status = "onboarding"
                company.save(update_fields=["lifecycle_status", "last_updated_date"])

            # link creator to company
            user.company = company
            user.status = User.Status.ACTIVE
            user.save(update_fields=["company", "status", "last_updated_date"])

            return api_response(200, "success", CompanySerializer(company).data)

        except Exception as exc:
            return self._handle_exception(exc, "create_company")

    # =======================================================
    # GET COMPANY DETAILS
    # =======================================================
    @extend_schema(
        summary="Get company details",
        responses={200: CompanySerializer},
    )
    @action(detail=True, methods=["get"], url_path="detail")
    def get_company(self, request, pk=None):
        try:
            company = (
                Company.objects
                .select_related("created_by")
                .filter(companyId=pk)
                .first()
            )

            if not company:
                return api_response(
                    404, "failure", {}, "NOT_FOUND", "Company not found."
                )

            # security: only members or platform admins may view
            if request.user.company != company and request.user.role not in [
                User.Role.PLATFORMADMIN,
                User.Role.SUPERADMIN,
            ]:
                return api_response(
                    403, "failure", {}, "FORBIDDEN", "Access denied."
                )

            return api_response(200, "success", CompanySerializer(company).data)

        except Exception as exc:
            return self._handle_exception(exc, "get_company")

    # =======================================================
    # UPDATE COMPANY
    # =======================================================
    @extend_schema(
        summary="Update company details",
        request=CompanySerializer,
        responses={200: CompanySerializer},
    )
    @action(detail=True, methods=["put"], url_path="update")
    @transaction.atomic
    def update_company(self, request, pk=None):
        try:
            user = request.user

            company = Company.objects.filter(companyId=pk).first()
            if not company:
                return api_response(
                    404, "failure", {}, "NOT_FOUND", "Company not found."
                )

            # security: ensure user belongs to this company or is platform admin
            if user.company != company and user.role not in [
                User.Role.PLATFORMADMIN,
                User.Role.SUPERADMIN,
            ]:
                return api_response(
                    403, "failure", {}, "FORBIDDEN", "You cannot update this company."
                )

            serializer = CompanySerializer(company, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # let serializer handle updating + team members
            company = serializer.save()

            return api_response(200, "success", CompanySerializer(company).data)

        except Exception as exc:
            return self._handle_exception(exc, "update_company")
