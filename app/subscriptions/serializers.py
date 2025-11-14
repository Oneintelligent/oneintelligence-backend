from rest_framework import serializers
from .models import Subscriptions, SubscriptionPlan

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "multiplier",
            "base_prices",
            "features",
            "has_trial",
            "trial_days",
            "global_discount_percentage",
            "status",
            "created_date",
            "last_updated_date"
        ]


class SubscriptionsSerializer(serializers.ModelSerializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlan.objects.all())
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = Subscriptions
        fields = [
            "subscriptionId",
            "plan",
            "plan_name",
            "companyId",
            "userId",
            "billing_type",
            "license_count",

            # Pricing details (read-only)
            "base_price_per_license",
            "final_price_per_license",
            "final_total_price",
            "applied_discount",

            # Trial logic
            "is_trial",
            "trial_text",

            # Dates & lifecycle
            "start_date",
            "end_date",
            "status",

            # Notes
            "notes",

            # Timestamps
            "created_date",
            "last_updated_date",
        ]

        read_only_fields = [
            "subscriptionId",
            "base_price_per_license",
            "final_price_per_license",
            "final_total_price",
            "applied_discount",
            "created_date",
            "last_updated_date",
        ]
