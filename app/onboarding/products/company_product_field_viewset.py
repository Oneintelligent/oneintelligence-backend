import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from app.utils.response import api_response
from app.products.models import CompanyProductField
from app.products.serializers import CompanyProductFieldSerializer

logger = logging.getLogger(__name__)


class CompanyProductFieldViewSet(viewsets.ModelViewSet):
    """
    Manage company-specific product fields.
    Allows listing, creating, updating, deleting, and toggling activation.
    """
    queryset = CompanyProductField.objects.select_related("company_product", "field")
    serializer_class = CompanyProductFieldSerializer

    def get_queryset(self):
        """
        Optionally filter by `company_product_id` query parameter.
        """
        queryset = self.queryset
        company_product_id = self.request.query_params.get("company_product_id")
        if company_product_id:
            queryset = queryset.filter(company_product_id=company_product_id)
        return queryset

    def list(self, request, *args, **kwargs):
        """
        List all company product fields (filtered by company_product_id if provided).
        """
        try:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            return api_response(status_code=0, status="success", data=serializer.data)
        except Exception as e:
            logger.exception("Error listing company product fields")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="LIST_COMPANY_PRODUCT_FIELDS_ERROR",
                error_message=str(e),
            )

    def create(self, request, *args, **kwargs):
        """
        Create a new company product field record.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            return api_response(
                status_code=0,
                status="success",
                data=self.get_serializer(obj).data,
            )
        except Exception as e:
            logger.exception("Error creating company product field")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="CREATE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

    def update(self, request, *args, **kwargs):
        """
        Update a company product field (full update).
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            return api_response(
                status_code=0,
                status="success",
                data=self.get_serializer(obj).data,
            )
        except Exception as e:
            logger.exception("Error updating company product field")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="UPDATE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a company product field.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            return api_response(
                status_code=0,
                status="success",
                data=self.get_serializer(obj).data,
            )
        except Exception as e:
            logger.exception("Error partially updating company product field")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="PARTIAL_UPDATE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a company product field record.
        """
        try:
            instance = self.get_object()
            instance.delete()
            return api_response(status_code=0, status="success", data={})
        except Exception as e:
            logger.exception("Error deleting company product field")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="DELETE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )

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
                data=self.get_serializer(instance).data,
            )
        except Exception as e:
            logger.exception("Error toggling company product field")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="TOGGLE_COMPANY_PRODUCT_FIELD_ERROR",
                error_message=str(e),
            )
