from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .models import User
import re

def validate_strong_password(password: str) -> str:
    """
    Validates password strength:
    - At least 8 characters
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    """
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

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'userId', 'companyId', 'subscriptionId',
            'first_name', 'last_name', 'email', 'phone', 'password',
            'role', 'profile_picture_url', 'language_preference', 'time_zone',
            'status', 'last_login_date', 'created_date', 'last_updated_date',
            'settings', 'authentication_type', 'two_factor_enabled'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if password:
            validated_data["password"] = make_password(password)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.password = make_password(password)
        instance.save()
        return instance


# ✅ Minimal serializer for signup
class SignUpSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    role = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone", "role"]

    def validate_email(self, value):
        """Ensure email is unique and valid in format."""
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email
    
    def validate_password(self, value):
        """Use shared password validation logic."""
        return validate_strong_password(value)

    def validate_phone(self, value):
        """Ensure phone number has only digits and length between 7–15."""
        phone_pattern = re.compile(r"^\+?[0-9]{7,15}$")
        if not phone_pattern.match(value):
            raise serializers.ValidationError("Enter a valid phone number (7–15 digits, optional +).")
        return value

    def create(self, validated_data):
        validated_data["email"] = validated_data["email"].strip().lower()
        password = validated_data.pop("password", None)
        if password:
            validated_data["password"] = make_password(password)
        
        return User.objects.create(**validated_data)


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        """Use shared password validation logic."""
        return validate_strong_password(value)

    def validate_email(self, value):
        # from .models import User
        normalized_email = value.strip().lower()
        try:
            user = User.objects.get(email__iexact=normalized_email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")

        if hasattr(user, "status") and user.status.lower() != "active":
            raise serializers.ValidationError("This account is inactive. Please contact support.")

        return normalized_email


class SignOutSerializer(serializers.Serializer):
    email = serializers.EmailField()
    refresh_token = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        """Ensure the email exists and belongs to an active user."""
        from .models import User
        normalized_email = value.strip().lower()

        try:
            user = User.objects.get(email__iexact=normalized_email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")

        if hasattr(user, "status") and user.status.lower() != "active":
            raise serializers.ValidationError("This account is inactive. Please contact support.")

        return normalized_email
    
class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password"]
