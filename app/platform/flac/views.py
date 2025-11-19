"""API endpoints for field-level access control (placeholder)."""
from rest_framework import viewsets, permissions

from .models import RoleFieldPolicy
from .serializers import RoleFieldPolicySerializer


class RoleFieldPolicyViewSet(viewsets.ModelViewSet):
    queryset = RoleFieldPolicy.objects.all()
    serializer_class = RoleFieldPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        company_id = getattr(self.request.user, "company_id", None)
        if company_id:
            return self.queryset.filter(company_id=company_id)
        return self.queryset.none()
