# app/onboarding/companies/serializers.py
from rest_framework import serializers
from app.onboarding.companies.models import Company
from app.products.models import Product
from app.onboarding.invites.models import InviteToken

class TeamMemberSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    role = serializers.CharField(required=False, default="User")
    status = serializers.CharField(required=False, default="Active")

    def validate_email(self, value):
        return value.strip().lower()

class CompanySetupSerializer(serializers.Serializer):
    company = serializers.DictField(child=serializers.CharField(), required=True)
    members = TeamMemberSerializer(many=True, required=False)
    modules = serializers.ListField(child=serializers.DictField(), required=False)
    plan = serializers.DictField(required=False)

    def validate(self, data):
        if "company" not in data:
            raise serializers.ValidationError("company field required")
        return data

class CompanySettingsSerializer(serializers.ModelSerializer):
    companyId = serializers.UUIDField(read_only=True)
    user_list = serializers.ListField(child=serializers.UUIDField(), read_only=True)
    subscription_ids = serializers.ListField(child=serializers.UUIDField(), read_only=True)
    product_ids = serializers.ListField(child=serializers.UUIDField(), read_only=True)

    class Meta:
        model = Company
        fields = [
            "companyId", "name", "description", "industry", "company_size",
            "email", "phone", "tags", "discount_percentage", "status",
            "payment_status", "user_list", "subscription_ids", "product_ids",
            "created_date", "last_updated_date"
        ]
        read_only_fields = ["companyId", "created_date", "last_updated_date"]

class CompanyDiscountSerializer(serializers.Serializer):
    discount_percentage = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=True
    )
