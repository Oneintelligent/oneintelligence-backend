# app/onboarding/users/serializers.py

import re
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from django.utils import timezone
from django.conf import settings

from app.platform.accounts.models import User, InviteToken
from app.platform.companies.models import Company


# =======================================================
# PASSWORD VALIDATION HELPER
# =======================================================
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


# =======================================================
# MINI USER SERIALIZER (lightweight, reused everywhere)
# =======================================================
class MiniUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["userId", "first_name", "last_name", "email", "role", "status"]


# =======================================================
# COMPANY SNIPPET INSIDE USER OBJECT
# (used in signin/signup/me response)
# =======================================================
class CompanyInUserSerializer(serializers.ModelSerializer):
    """
    Lightweight company serializer for use inside User objects.
    Does NOT include users to avoid circular references and keep /users/me/ lightweight.
    Use /companies/{id}/detail/ when you need company with users.
    """

    class Meta:
        model = Company
        fields = [
            "companyId",
            "name",
            "email",
            "phone",
            "address",
            "country",
            "industry",
            "company_size",
            "website",
            "logo_url",
            "time_zone",
            "language",
            "plan",
            "lifecycle_status",
            "products",
            "workspace_limit",
            "storage_limit_mb",
            "ai_enabled",
            "monthly_ai_quota",
            "created_date",
            "last_updated_date",
        ]


# =======================================================
# MAIN USER SERIALIZER (EXCLUDES PASSWORD)
# =======================================================
class UserWithCompanySerializer(serializers.ModelSerializer):
    company = CompanyInUserSerializer(read_only=True)

    class Meta:
        model = User
        exclude = ["password", "is_superuser", "is_staff"]
        read_only_fields = ["email_verified", "email_verified_at", "last_password_change"]


# =======================================================
# SIGN-UP
# =======================================================
class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    companyId = serializers.UUIDField(required=False)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone", "role", "companyId"]

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Email already exists.")
        return email

    def validate_password(self, value):
        return validate_strong_password(value)

    def create(self, validated_data):
        raw_pwd = validated_data.pop("password")
        company_id = validated_data.pop("companyId", None)

        email = validated_data.pop("email").lower().strip()  # pop email here

        # optional: attach company
        company = None
        if company_id:
            company = Company.objects.filter(companyId=company_id).first()

        user = User.objects.create(
            **validated_data,
            company=company,
            email=email,
            password=make_password(raw_pwd),
            status=User.Status.ACTIVE,
        )
        return user


# =======================================================
# SIGN-IN (AUTH ONLY — DO NOT LEAK ACCOUNT EXISTENCE)
# =======================================================
class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


# =======================================================
# USER PROFILE UPDATE
# =======================================================
class UserProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    profile_picture_url = serializers.CharField(required=False, allow_blank=True)
    language_preference = serializers.CharField(required=False, allow_blank=True)
    time_zone = serializers.CharField(required=False, allow_blank=True)
    preferences = serializers.DictField(required=False)

    def validate_email(self, value):
        email = value.lower().strip()
        user = self.context["request"].user

        if User.objects.exclude(userId=user.userId).filter(email__iexact=email).exists():
            raise serializers.ValidationError("This email is already used by another account.")

        return email


# =======================================================
# INVITE USER
# =======================================================
class InviteUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.USER)

    def validate_email(self, value):
        email = value.lower().strip()
        existing = User.objects.filter(email__iexact=email).first()

        if existing and existing.status == User.Status.ACTIVE:
            raise serializers.ValidationError("A user with this email already exists and is active.")

        return email


# =======================================================
# ACCEPT INVITE
# =======================================================
class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        token = str(attrs["token"]).strip()
        password = attrs["password"]

        invite = InviteToken.objects.filter(token=token).first()

        if not invite or not invite.is_valid():
            raise serializers.ValidationError("Invalid or expired invite token.")

        validate_strong_password(password)

        attrs["invite"] = invite
        return attrs

    def save(self):
        invite = self.validated_data["invite"]
        password = self.validated_data["password"]

        user = invite.user
        user.set_password(password)
        user.status = User.Status.ACTIVE
        user.save(update_fields=["password", "status"])

        invite.delete()
        return user


# =======================================================
# TEAM MEMBER UPDATE (role/status)
# =======================================================
class TeamMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    status = serializers.ChoiceField(choices=User.Status.choices, required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)


# =======================================================
# PASSWORD RESET
# =======================================================
class PasswordResetSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        return validate_strong_password(value)
