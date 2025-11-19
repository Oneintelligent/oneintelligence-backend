"""Licensing viewsets (placeholder)."""
from rest_framework import viewsets, permissions

from .models import SeatBucket, CompanyLicense
from .serializers import SeatBucketSerializer, CompanyLicenseSerializer


class SeatBucketViewSet(viewsets.ModelViewSet):
    queryset = SeatBucket.objects.all()
    serializer_class = SeatBucketSerializer
    permission_classes = [permissions.IsAdminUser]


class CompanyLicenseViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyLicenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        company_id = getattr(self.request.user, "company_id", None)
        qs = CompanyLicense.objects.all()
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

