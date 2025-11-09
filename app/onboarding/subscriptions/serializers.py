from rest_framework import serializers
from .models import Subscriptions
from app.onboarding.users.models import Users
from app.onboarding.companies.models import Company
from app.onboarding.users.serializers import UsersSerializer
from app.onboarding.companies.serializers import CompanySerializer

class SubscriptionsSerializer(serializers.ModelSerializer):
    user = UsersSerializer(read_only=True)
    company = CompanySerializer(read_only=True)

    class Meta:
        model = Subscriptions
        fields = [
            "subscriptionId",
            "company",
            "user",
            "plan",
            "billing_type",
            "license_count",
            "price_per_license",
            "start_date",
            "end_date",
            "status",
            "created_date",
            "last_updated_date",
        ]

    def validate(self, attrs):
        user = attrs.get("user")
        company = attrs.get("company")
        if user and user.companyId != company:
            raise serializers.ValidationError("User must belong to the selected company.")
        return attrs
