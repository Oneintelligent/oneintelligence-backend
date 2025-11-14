# app/onboarding/companies/update_modules.py
import logging
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.utils.response import api_response
from app.onboarding.companies.models import Company
from app.products.models import Product
from app.onboarding.companies.serializers import ModuleUpdateSerializer
from app.onboarding.companies.permissions import is_owner, is_company_admin

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Products"],
    summary="Update company modules / products",
    description="Owner or Admin may update which modules the company uses. This creates products if missing.",
    request=ModuleUpdateSerializer,
    responses={200: OpenApiResponse(description="Modules updated")}
)
class CompanyModulesUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, companyId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Not allowed to update modules")

        serializer = ModuleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        modules = serializer.validated_data.get("modules", [])
        product_ids = []
        for mod in modules:
            code = (mod.get("id") or mod.get("code") or mod.get("title") or "").upper()
            if not code:
                continue
            product, _ = Product.objects.update_or_create(
                code=code,
                defaults={"name": mod.get("title", code), "description": mod.get("description", ""), "status": Product.StatusChoices.ACTIVE}
            )
            product_ids.append(str(product.productId))

        company.product_ids = product_ids
        company.save(update_fields=["product_ids", "last_updated_date"])

        return api_response(status_code=status.HTTP_200_OK, status="success", data={"product_ids": product_ids})
