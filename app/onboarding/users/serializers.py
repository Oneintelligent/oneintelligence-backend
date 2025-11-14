from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User
from app.onboarding.companies.models import Company
import re


# -------------------------
# company mini serializer
# -------------------------
# app/onboarding/users/serializers.py

class CompanyMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "companyId",
            "name",
            "email",
            "phone",
            "address",
            "country",
        ]



# -------------------------
# unified user + company serializer
# -------------------------
class UserWithCompanySerializer(serializers.ModelSerializer):
    company = CompanyMiniSerializer(read_only=True)

    class Meta:
        model = User
        exclude = ["password"]


# -------------------------
# signup serializer
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
