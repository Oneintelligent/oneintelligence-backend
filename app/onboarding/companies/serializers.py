from rest_framework import serializers
from app.onboarding.companies.models import Company
from app.onboarding.users.models import User
from app.onboarding.users.serializers import UserWithCompanySerializer


class CompanySerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "companyId",
            "name",
            "email",
            "phone",
            "address",
            "country",
            "created_by_user",
            "created_date",
            "last_updated_date",
            "users",
        ]
        read_only_fields = [
            "companyId",
            "created_by_user",
            "created_date",
            "last_updated_date",
        ]

    def get_users(self, company):
        qs = User.objects.filter(company=company).select_related("company")
        return UserWithCompanySerializer(qs, many=True).data
