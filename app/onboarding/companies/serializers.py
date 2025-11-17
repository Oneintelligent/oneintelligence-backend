# app/onboarding/companies/serializers.py

from rest_framework import serializers
from django.db import transaction

from app.onboarding.companies.models import Company
from app.onboarding.users.models import User
from app.onboarding.users.serializers import MiniUserSerializer


# =======================================================
# PRIMARY COMPANY SERIALIZER (read / write)
# =======================================================
class CompanySerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    # Incoming list from frontend
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
            "created_by",
            "created_date",
            "last_updated_date",
            "plan",
            "products",
            "users",
            "team_members",
        ]
        read_only_fields = [
            "companyId",
            "created_by",
            "created_date",
            "last_updated_date",
            "users",
        ]

    # ----------------------------------------------------
    # USERS LIST ON COMPANY
    # ----------------------------------------------------
    def get_users(self, company):
        qs = (
            User.objects.filter(company=company)
            .select_related("company")
            .order_by("created_date")
        )
        return MiniUserSerializer(qs, many=True).data

    # ----------------------------------------------------
    # CREATE COMPANY + TEAM MEMBERS
    # ----------------------------------------------------
    @transaction.atomic
    def create(self, validated_data):
        team_members = validated_data.pop("team_members", [])
        company = Company.objects.create(**validated_data)

        self._process_team_members(company, team_members)
        return company

    # ----------------------------------------------------
    # UPDATE COMPANY + TEAM MEMBERS
    # ----------------------------------------------------
    @transaction.atomic
    def update(self, instance, validated_data):
        team_members = validated_data.pop("team_members", [])

        # update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._process_team_members(instance, team_members)
        return instance

    # ----------------------------------------------------
    # INTERNAL: TEAM MEMBER CREATION/UPDATE LOGIC
    # ----------------------------------------------------
    def _process_team_members(self, company, members):

        for m in members:
            email = m.get("email", "").lower().strip()
            if not email:
                continue

            first_name = m.get("first_name", "")
            last_name = m.get("last_name", "")
            role = m.get("role", User.Role.USER)

            # --------------------------------------------
            # STEP 1 — Does this user already exist?
            # --------------------------------------------
            user = User.objects.filter(email__iexact=email).first()

            # --------------------------------------------
            # STEP 2 — User exists BUT belongs to another company?
            # Prevent cross-company hijack.
            # --------------------------------------------
            if user and user.company and user.company != company:
                raise serializers.ValidationError(
                    f"User {email} already belongs to another company."
                )

            # --------------------------------------------
            # STEP 3 — Create NEW USER (Pending)
            # --------------------------------------------
            if not user:
                user = User.objects.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    company=company,
                    role=role,
                    status=User.Status.PENDING,  # invited, not active
                )
                # Note: invite token email workflow happens in the view, not here.
                continue

            # --------------------------------------------
            # STEP 4 — Existing user: update minimal fields
            # --------------------------------------------
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.role = role
            user.company = company
            user.save(update_fields=["first_name", "last_name", "role", "company"])
