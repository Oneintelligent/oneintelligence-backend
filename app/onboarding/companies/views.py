import logging
from rest_framework import viewsets
from rest_framework.permissions import AllowAny  # ✅ change this import
from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import CompanySerializer
from app.utils.response import api_response

logger = logging.getLogger(__name__)

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('-created_date')
    serializer_class = CompanySerializer
    permission_classes = [AllowAny]  # ✅ anyone can access this endpoint

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return api_response(0, "success", serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(0, "success", serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(0, "success", serializer.data)
