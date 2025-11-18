# app/sales/serializers.py
from rest_framework import serializers
from .models import Account, Lead, Opportunity, Activity
from django.conf import settings
from app.teams.models import Team
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------
# Minimal user reference serializer (DRF-safe, schema-safe)
# ---------------------------------------------------------
class UserRefSerializer(serializers.Serializer):
    userId = serializers.UUIDField()
    id = serializers.UUIDField(required=False)
    email = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)


class TeamRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("team_id", "name")


# ---------------------------------------------------------
# Account
# ---------------------------------------------------------
class AccountSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    team = TeamRefSerializer(read_only=True)
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Account
        fields = "__all__"
        read_only_fields = ("account_id", "created_at", "updated_at", "health_score")

    def create(self, validated_data):
        team_id = validated_data.pop("team_id", None)
        instance = super().create(validated_data)

        if team_id:
            try:
                instance.team = Team.objects.get(team_id=team_id, company=instance.company)
                instance.save()
            except Team.DoesNotExist:
                pass
        return instance

    def update(self, instance, validated_data):
        team_id = validated_data.pop("team_id", None)
        instance = super().update(instance, validated_data)

        if team_id is not None:
            try:
                instance.team = Team.objects.get(team_id=team_id, company=instance.company)
            except Team.DoesNotExist:
                instance.team = None
            instance.save()

        return instance


# ---------------------------------------------------------
# Lead
# ---------------------------------------------------------
class LeadCreateSerializer(serializers.ModelSerializer):
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Lead
        exclude = ("lead_id", "company", "score", "ai_reasons", "created_at", "updated_at")
        extra_kwargs = {
            "shared_with": {"required": False},
            "visibility": {"required": False},
        }

    def create(self, validated_data):
        team_id = validated_data.pop("team_id", None)
        lead = super().create(validated_data)

        if team_id:
            try:
                lead.team = Team.objects.get(team_id=team_id, company=lead.company)
                lead.save()
            except Team.DoesNotExist:
                pass

        return lead


class LeadSerializer(serializers.ModelSerializer):
    owner = UserRefSerializer(read_only=True)
    team = TeamRefSerializer(read_only=True)
    account = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = ("lead_id", "company", "score", "ai_reasons", "created_at", "updated_at")


# ---------------------------------------------------------
# Opportunity
# ---------------------------------------------------------
class OpportunityCreateSerializer(serializers.ModelSerializer):
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Opportunity
        exclude = ("opp_id", "company", "created_at", "updated_at")
        extra_kwargs = {"shared_with": {"required": False}, "visibility": {"required": False}}

    def create(self, validated_data):
        team_id = validated_data.pop("team_id", None)
        opp = super().create(validated_data)

        if team_id:
            try:
                opp.team = Team.objects.get(team_id=team_id, company=opp.company)
                opp.save()
            except Team.DoesNotExist:
                pass

        return opp


class OpportunitySerializer(serializers.ModelSerializer):
    owner = UserRefSerializer(read_only=True)
    team = TeamRefSerializer(read_only=True)
    account = serializers.PrimaryKeyRelatedField(read_only=True)
    lead = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Opportunity
        fields = "__all__"
        read_only_fields = ("opp_id", "company", "created_at", "updated_at")


# ---------------------------------------------------------
# Activity
# ---------------------------------------------------------
class ActivityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            "entity_type",
            "entity_id",
            "kind",
            "body",
            "metadata",
            "occurred_at",
        ]


class ActivitySerializer(serializers.ModelSerializer):
    actor = UserRefSerializer(read_only=True)

    class Meta:
        model = Activity
        fields = "__all__"
        read_only_fields = ("activity_id", "company", "created_at")
