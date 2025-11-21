"""
Onboarding Serializers
Clean, scalable serializers for onboarding flow with RBAC integration
"""

from rest_framework import serializers
from app.platform.accounts.models import User
from app.platform.companies.models import Company
from app.platform.subscriptions.models import Subscriptions
from app.platform.products.models import CompanyModule
from app.platform.rbac.utils import get_user_roles, get_user_primary_role
from app.platform.rbac.helpers import get_user_primary_role as get_primary_role


class OnboardingStatusSerializer(serializers.Serializer):
    """Serializer for onboarding status response."""
    
    progress = serializers.DictField()
    steps = serializers.DictField()
    can_proceed_to_activation = serializers.BooleanField()


class UserRoleSerializer(serializers.Serializer):
    """Serializer for user role information."""
    code = serializers.CharField()
    display_name = serializers.CharField()


class TeamMemberSerializer(serializers.Serializer):
    """Serializer for team member with RBAC roles."""
    userId = serializers.UUIDField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    roles = UserRoleSerializer(many=True)
    primary_role = UserRoleSerializer(required=False, allow_null=True)

