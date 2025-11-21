"""
Consent Management Serializers
"""

from rest_framework import serializers
from .models import UserConsent, ConsentType


class UserConsentSerializer(serializers.ModelSerializer):
    """Serializer for user consent"""
    
    consent_type_display = serializers.CharField(
        source="get_consent_type_display",
        read_only=True
    )
    
    class Meta:
        model = UserConsent
        fields = [
            "id",
            "consent_type",
            "consent_type_display",
            "granted",
            "granted_at",
            "revoked_at",
            "version",
            "consent_text",
            "created_date",
            "last_updated_date",
        ]
        read_only_fields = [
            "id",
            "granted_at",
            "revoked_at",
            "created_date",
            "last_updated_date",
        ]


class ConsentUpdateSerializer(serializers.Serializer):
    """Serializer for updating consent"""
    
    consent_type = serializers.ChoiceField(
        choices=ConsentType.choices,
        required=True
    )
    
    granted = serializers.BooleanField(
        required=True
    )
    
    consent_text = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional: The exact text user is consenting to"
    )


class ConsentStatusSerializer(serializers.Serializer):
    """Serializer for consent status response"""
    
    ai_usage = serializers.BooleanField()
    data_storage = serializers.BooleanField()
    marketing = serializers.BooleanField()
    analytics = serializers.BooleanField()
    
    last_updated = serializers.DateTimeField(required=False)

