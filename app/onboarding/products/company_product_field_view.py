import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from app.utils.response import api_response
from app.onboarding.products.models import CompanyProductField
from app.onboarding.products.serializers import CompanyProductFieldSerializer

logger = logging.getLogger(__name__)


class CompanyProductFieldViewSet(viewsets.ModelViewSet):
    """
    Manage company-specific product fields.
    Includes CRUD + toggle endpoints.
    """

    queryset = CompanyProductField.objects.select_related("company_product", "field")
    serializer_class = CompanyProductFieldSerializer

    def get_queryset(self):
        """
        Optionally filter by company_product_id.
        """
        queryset = self.queryset
        company_product_id = self.request.query_params.get("company_product_id")
        if company_product_id:
            queryset = queryset.filter(company_product_id=company_product_id)
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error listing company product fields")
            return api_response(
                status_code=1,
                status="failure",
                error_code="LIST_COMPANY_PRODUCT_FIELDS_ERROR",
                error_message=str(e),
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            return api_response(status_code=0, status="success", data=self.get_serializer(obj).data)
        except Exception as e:
            logger.exception("Error creating company product field")
            return api_response(
                status_code=1,
                status="failure",
                error_code="CREATE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            return api_response(status_code=0, status="success", data=self.get_serializer(obj).data)
        except Exception as e:
            logger.exception("Error updating company product field")
            return api_response(
                status_code=1,
                status="failure",
                error_code="UPDATE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            return api_response(status_code=0, status="success", data=self.get_serializer(obj).data)
        except Exception as e:
            logger.exception("Error partially updating company product field")
            return api_response(
                status_code=1,
                status="failure",
                error_code="PARTIAL_UPDATE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return api_response(status_code=0, status="success", data={})
        except Exception as e:
            logger.exception("Error deleting company product field")
            return api_response(
                status_code=1,
                status="failure",
                error_code="DELETE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

    # ✅ Toggle endpoint
    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """
        Toggle the active/inactive status of a company product field.
        """
        try:
            instance = self.get_object()
            instance.is_active = not instance.is_active
            instance.save()
            return api_response(
                status_code=0,
                status="success",
                data={
                    "id": instance.id,
                    "fieldId": str(instance.field.fieldId),
                    "field_name": instance.field.name,
                    "is_active": instance.is_active,
                },
            )
        except Exception as e:
            logger.exception("Error toggling company product field")
            return api_response(
                status_code=1,
                status="failure",
                error_code="TOGGLE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )
