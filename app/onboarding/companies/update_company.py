# app/onboarding/companies/update_company.py
import logging
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.utils.response import api_response
from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import CompanySettingsSerializer
from app.onboarding.companies.permissions import is_owner, is_company_admin, is_platform_admin
from app.onboarding.companies.serializers_full import CompanyFullSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Company Settings"],
    summary="Get or update company settings",
    description=(
        "GET returns the company settings. PUT updates editable fields. "
        "Only the company owner or admins may update settings; discount modification is platform-only."
        "\n\nAuthentication: `Authorization: Bearer <access_token>`."
    ),
    request=CompanySettingsSerializer,
    responses={
        200: OpenApiResponse(description="Company settings"),
        403: OpenApiResponse(description="Forbidden"),
        404: OpenApiResponse(description="Company not found"),
    }
)
class CompanySettingsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_company(self, companyId):
        return Company.objects.filter(companyId=companyId).first()

    def get(self, request, companyId):
        company = self.get_company(companyId)
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        serializer = CompanyFullSerializer(company)
        return api_response(200, "success", serializer.data)

    @transaction.atomic
    def put(self, request, companyId):
        company = self.get_company(companyId)
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        current_user = request.user
        if not (is_owner(current_user, company) or is_company_admin(current_user, company)):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Not allowed to update company settings")

        serializer = CompanySettingsSerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            # Prevent non-owner from changing discount
            if "discount_percentage" in serializer.validated_data and not is_owner(current_user, company) and not is_platform_admin(current_user):
                return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Only owner or platform admin can change discount")
            serializer.save()
            return api_response(status_code=status.HTTP_200_OK, status="success", data=serializer.data)
        else:
            return api_response(status_code=status.HTTP_400_BAD_REQUEST, status="error", data={}, error_code="VALIDATION_ERROR", error_message=serializer.errors)
