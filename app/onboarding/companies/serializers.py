from rest_framework import serializers
from app.onboarding.companies.models import Company
from app.onboarding.users.models import User
from app.onboarding.users.serializers import UserWithCompanySerializer


class CompanySerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    # NEW FIELD: allows frontend to pass team members
    team_members = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

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
            "plan",
            "products",    
            # NEW
            "team_members",
        ]
        read_only_fields = [
            "companyId",
            "created_by_user",
            "created_date",
            "last_updated_date",
            "users",
        ]

    def get_users(self, company):
        qs = User.objects.filter(company=company).select_related("company")
        return UserWithCompanySerializer(qs, many=True).data

    #
    # CREATE COMPANY + TEAM MEMBERS
    #
    def create(self, validated_data):
        team_members = validated_data.pop("team_members", [])

        company = Company.objects.create(**validated_data)

        # Process user creation
        self._process_team_members(company, team_members)

        return company

    #
    # UPDATE COMPANY + TEAM MEMBERS
    #
    def update(self, instance, validated_data):
        team_members = validated_data.pop("team_members", [])

        # Update company fields normally
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Add/update team members
        self._process_team_members(instance, team_members)

        return instance

    #
    # INTERNAL HELPER
    #
    def _process_team_members(self, company, members):
        for m in members:
            email = m.get("email")
            if not email:
                continue

            first_name = m.get("first_name", "")
            last_name = m.get("last_name", "")
            role = m.get("role", "User")

            # Check if user exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "company": company,
                },
            )

            # If user already exists: update role + company
            if not created:
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.role = role
                user.company = company

            user.save(update_fields=["first_name", "last_name", "role", "company"])
