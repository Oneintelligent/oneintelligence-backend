import logging
from rest_framework import viewsets, status
from .models import Company
from .serializers import CompanySerializer
from app.utils.response import api_response  # Base response helper

logger = logging.getLogger(__name__)

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return api_response(
                status_code=0,
                status="success",
                data=serializer.data
            )
        except Exception as e:
            logger.exception("Error listing companies")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="LIST_COMPANIES_ERROR",
                error_message=str(e)
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return api_response(
                status_code=0,
                status="success",
                data=serializer.data
            )
        except Exception as e:
            logger.exception("Error retrieving company")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="RETRIEVE_COMPANY_ERROR",
                error_message=str(e)
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    status_code=0,
                    status="success",
                    data=serializer.data
                )
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=serializer.errors
            )
        except Exception as e:
            logger.exception("Error creating company")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="CREATE_COMPANY_ERROR",
                error_message=str(e)
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=False)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    status_code=0,
                    status="success",
                    data=serializer.data
                )
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=serializer.errors
            )
        except Exception as e:
            logger.exception("Error updating company")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="UPDATE_COMPANY_ERROR",
                error_message=str(e)
            )

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    status_code=0,
                    status="success",
                    data=serializer.data
                )
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=serializer.errors
            )
        except Exception as e:
            logger.exception("Error partially updating company")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="PARTIAL_UPDATE_COMPANY_ERROR",
                error_message=str(e)
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return api_response(
                status_code=0,
                status="success",
                data={}
            )
        except Exception as e:
            logger.exception("Error deleting company")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="DELETE_COMPANY_ERROR",
                error_message=str(e)
            )
