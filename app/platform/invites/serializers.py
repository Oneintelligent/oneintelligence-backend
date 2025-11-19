# app/onboarding/invites/serializers.py
from rest_framework import serializers
from app.platform.invites.models import InviteToken
from app.platform.accounts.serializers import validate_strong_password

class InviteTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = InviteToken
        fields = ["token", "invited_user_email", "companyId", "inviter_user_id", "expires_at", "used"]
        read_only_fields = ["token", "expires_at", "used"]

class InviteAcceptSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        return validate_strong_password(value)
