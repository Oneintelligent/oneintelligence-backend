from rest_framework import serializers
from app.onboarding.companies.models import Company


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
        extra_kwargs = {
            'name': {'required': True},
            'created_by_user_id': {'required': True},
        }
