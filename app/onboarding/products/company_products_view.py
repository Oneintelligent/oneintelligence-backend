import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from app.utils.response import api_response
from .models import Product, CompanyProduct, CompanyProductField
from .serializers import ProductSerializer, CompanyProductFieldSerializer

logger = logging.getLogger(__name__)


class CompanyProductsViewSet(viewsets.ViewSet):
    """
    Lists all products and their fields (both active/inactive) for a company.
    Allows manual activation/deactivation of products.
    """

    def list(self, request):
        try:
            company_id = request.query_params.get("company_id")
            if not company_id:
                return api_response(
                    status_code=1,
                    status="failure",
                    error_code="MISSING_COMPANY_ID",
                    error_message="company_id is required",
                )

            products = Product.objects.prefetch_related("fields").all()
            company_products = {cp.product_id: cp for cp in CompanyProduct.objects.filter(company_id=company_id)}
            company_field_status = {
                (cf.field_id, cf.company_product_id): cf.is_active
                for cf in CompanyProductField.objects.filter(company_product__company_id=company_id)
            }

            data = []
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

                data.append({
                    "productId": str(product.productId),
                    "name": product.name,
                    "description": product.description,
                    "is_active": is_product_active,
                    "fields": fields_data,
                })

            return api_response(status_code=0, status="success", data=data)

        except Exception as e:
            logger.exception("Error listing company products")
            return api_response(status_code=1, status="failure", error_code="LIST_COMPANY_PRODUCTS_ERROR", error_message=str(e))

    @action(detail=True, methods=["post"])
    def toggle_product(self, request, pk=None):
        """
        Toggle activation for a company’s product.
        """
        try:
            company_id = request.data.get("company_id")
            if not company_id:
                return api_response(status_code=1, status="failure", error_code="MISSING_COMPANY_ID", error_message="company_id is required")

            company_product, _ = CompanyProduct.objects.get_or_create(company_id=company_id, product_id=pk)
            company_product.is_active = not company_product.is_active
            company_product.save()

            return api_response(status_code=0, status="success", data={
                "productId": pk,
                "is_active": company_product.is_active,
            })

        except Exception as e:
            logger.exception("Error toggling company product")
            return api_response(status_code=1, status="failure", error_code="TOGGLE_COMPANY_PRODUCT_ERROR", error_message=str(e))
