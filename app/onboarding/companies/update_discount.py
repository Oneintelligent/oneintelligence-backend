# app/onboarding/companies/update_discount.py
import logging
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.utils.response import api_response
from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import CompanyDiscountSerializer
from app.onboarding.companies.permissions import is_platform_admin

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Company Admin"],
    summary="Update company discount (PlatformAdmin only)",
    description=(
        "Internal OneIntelligence platform admins can update the company-level discount percentage (0-100)."
        "\n\nAuthentication: `Authorization: Bearer <access_token>`"
    ),
    request=CompanyDiscountSerializer,
    responses={
        200: OpenApiResponse(description="Discount updated successfully"),
        403: OpenApiResponse(description="Forbidden"),
        404: OpenApiResponse(description="Company not found"),
    }
)
class CompanyDiscountUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, companyId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        if not is_platform_admin(request.user):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Only platform admins can update discounts")

        serializer = CompanyDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        discount = serializer.validated_data["discount_percentage"]

        company.discount_percentage = discount
        company.save(update_fields=["discount_percentage", "last_updated_date"])

        return api_response(status_code=status.HTTP_200_OK, status="success", data={"companyId": str(company.companyId), "discount_percentage": discount, "updated_by": request.user.email})
