import logging
from rest_framework import viewsets
from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import CompanySerializer
from app.utils.response import api_response

logger = logging.getLogger(__name__)

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('-created_date')
    serializer_class = CompanySerializer

    def handle_exception(self, e, code, message):
        logger.exception(message)
        return api_response(
            status_code=1,
            status="failure",
            data={},
            error_code=code,
            error_message=str(e)
        )

    def list(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            return api_response(0, "success", serializer.data)
        except Exception as e:
            return self.handle_exception(e, "LIST_COMPANIES_ERROR", "Error listing companies")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return api_response(0, "success", serializer.data)
        except Exception as e:
            return self.handle_exception(e, "RETRIEVE_COMPANY_ERROR", "Error retrieving company")

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return api_response(0, "success", serializer.data)
            return api_response(1, "failure", {}, "VALIDATION_ERROR", serializer.errors)
        except Exception as e:
            return self.handle_exception(e, "CREATE_COMPANY_ERROR", "Error creating company")

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return api_response(0, "success", serializer.data)
            return api_response(1, "failure", {}, "VALIDATION_ERROR", serializer.errors)
        except Exception as e:
            return self.handle_exception(e, "UPDATE_COMPANY_ERROR", "Error updating company")

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return api_response(0, "success", serializer.data)
            return api_response(1, "failure", {}, "VALIDATION_ERROR", serializer.errors)
        except Exception as e:
            return self.handle_exception(e, "PARTIAL_UPDATE_COMPANY_ERROR", "Error partially updating company")
