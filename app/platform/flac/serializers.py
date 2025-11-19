"""Serializers for field-level access control (placeholder)."""
from rest_framework import serializers

from .models import RoleFieldPolicy


class RoleFieldPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleFieldPolicy
        fields = "__all__"
