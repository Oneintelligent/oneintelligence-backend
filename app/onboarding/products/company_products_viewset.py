import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from app.utils.response import api_response
from .models import Product, CompanyProduct, CompanyProductField, ProductField
from .serializers import ProductSerializer
from django.db.models import Prefetch

logger = logging.getLogger(__name__)

class CompanyProductsViewSet(viewsets.ViewSet):
    """
    Lists all products and their fields (both active/inactive) for a company.
    Allows manual activation/deactivation of products and fields.
    """

    def list(self, request, *args, **kwargs):
        try:
            company_id = request.query_params.get("company_id")
            if not company_id:
                return api_response(
                    status_code=1, status="failure", data={},
                    error_code="MISSING_COMPANY_ID",
                    error_message="company_id is required"
                )

            # Fetch all master products and fields
            products = Product.objects.prefetch_related("fields").all()

            # Fetch company-level activation data
            company_products = {cp.product_id: cp for cp in CompanyProduct.objects.filter(company_id=company_id)}
            company_field_status = {
                (cf.field_id, cf.company_product_id): cf.is_active
                for cf in CompanyProductField.objects.filter(company_product__company_id=company_id)
            }

            response_data = []

            for product in products:
                company_product = company_products.get(product.productId)
                is_product_active = company_product.is_active if company_product else False

                fields_data = []
                for field in product.fields.all():
                    is_field_active = False
                    if company_product:
                        is_field_active = company_field_status.get((field.fieldId, company_product.id), False)

                    fields_data.append({
                        "fieldId": str(field.fieldId),
                        "name": field.name,
                        "data_type": field.data_type,
                        "is_active": is_field_active,
                    })

                response_data.append({
                    "productId": str(product.productId),
                    "name": product.name,
                    "description": product.description,
                    "is_active": is_product_active,
                    "fields": fields_data,
                })

            return api_response(status_code=0, status="success", data=response_data)

        except Exception as e:
            logger.exception("Error listing products for company")
            return api_response(
                status_code=1, status="failure", data={},
                error_code="LIST_COMPANY_PRODUCTS_ERROR", error_message=str(e)
            )

    @action(detail=True, methods=["post"])
    def toggle_product(self, request, pk=None):
        """
        Toggle product activation for a company.
        """
        try:
            company_id = request.data.get("company_id")
            if not company_id:
                return api_response(status_code=1, status="failure", data={},
                    error_code="MISSING_COMPANY_ID", error_message="company_id is required")

            company_product, _ = CompanyProduct.objects.get_or_create(
                company_id=company_id, product_id=pk
            )
            company_product.is_active = not company_product.is_active
            company_product.save()

            return api_response(status_code=0, status="success", data={
                "productId": pk,
                "is_active": company_product.is_active
            })

        except Exception as e:
            logger.exception("Error toggling product")
            return api_response(
                status_code=1, status="failure", data={},
                error_code="TOGGLE_COMPANY_PRODUCT_ERROR", error_message=str(e)
            )
