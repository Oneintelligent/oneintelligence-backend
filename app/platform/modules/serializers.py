"""Serializers for module registry."""
from rest_framework import serializers

from .models import ModuleDefinition, CompanyModule


class ModuleDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleDefinition
        fields = "__all__"


class CompanyModuleSerializer(serializers.ModelSerializer):
    module = ModuleDefinitionSerializer(read_only=True)
    module_id = serializers.PrimaryKeyRelatedField(
        queryset=ModuleDefinition.objects.all(),
        source="module",
        write_only=True,
    )

    class Meta:
        model = CompanyModule
        fields = "__all__"

