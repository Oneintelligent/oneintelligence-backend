# app/onboarding/users/serializers.py

import re
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from app.onboarding.companies.models import Company
from app.onboarding.users.models import User
from .models import InviteToken

# Mini user serializer (reusable)
class MiniUserForTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["userId", "first_name", "last_name", "email", "role", "status"]


# -------------------------
# helper: password strength
# -------------------------
def validate_strong_password(password: str) -> str:
    if len(password) < 8:
        raise serializers.ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise serializers.ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise serializers.ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise serializers.ValidationError("Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise serializers.ValidationError("Password must contain at least one special character.")
    return password


# -------------------------
# signup serializer
# -------------------------
class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone", "role"]

    def validate_email(self, value):
        v = value.lower().strip()
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Email already exists.")
        return v

    def validate_password(self, value):
        return validate_strong_password(value)

    def create(self, validated_data):
        raw_pwd = validated_data.pop("password")
        validated_data["email"] = validated_data["email"].lower().strip()
        validated_data["password"] = make_password(raw_pwd)
        return User.objects.create(**validated_data)


# -------------------------
# signin serializer (no strength check)
# -------------------------
class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        v = value.lower().strip()
        if not User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("No account found with this email.")
        return v


# -------------------------
# profile update serializer
# -------------------------
class UserProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    profile_picture_url = serializers.CharField(required=False, allow_blank=True)
    language_preference = serializers.CharField(required=False, allow_blank=True)
    time_zone = serializers.CharField(required=False, allow_blank=True)
    settings = serializers.DictField(required=False)


# -----------------------------------------
# USER OBJECT USED INSIDE COMPANY RESPONSE
# -----------------------------------------
class MiniUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["userId", "first_name", "last_name", "email", "role", "status"]


# -----------------------------------------
# COMPANY SERIALIZER FOR AUTH RESPONSES
# includes plan, products and users list
# -----------------------------------------
class CompanyInUserSerializer(serializers.ModelSerializer):
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
            "plan",
            "products",
            "users",
        ]

    def get_users(self, company):
        qs = User.objects.filter(company=company).order_by("created_date")
        return MiniUserSerializer(qs, many=True).data


# ---------------------------------------------------------
# MAIN SERIALIZER: USER + COMPANY (USED IN SIGNIN / SIGNUP / ME)
# ---------------------------------------------------------
class UserWithCompanySerializer(serializers.ModelSerializer):
    company = CompanyInUserSerializer(read_only=True)

    class Meta:
        model = User
        exclude = ["password"]



# Invite serializer (request)
class InviteUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.USER)

    def validate_email(self, value):
        # If a user with email already exists and is Active, block
        existing = User.objects.filter(email__iexact=value.strip().lower()).first()
        if existing and existing.status == User.Status.ACTIVE:
            raise serializers.ValidationError("A user with this email already exists.")
        return value.strip().lower()

# Set password (accept invite)
class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        # reuse your password policy if desired; keep simple here
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return value

# Update user (role/status)
class TeamMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    status = serializers.ChoiceField(choices=User.Status.choices, required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
