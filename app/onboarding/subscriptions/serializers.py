from rest_framework import serializers
from .models import Subscriptions

class SubscriptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriptions
        fields = [
            "subscriptionId",
            "companyId",
            "userId",
            "plan",
            "billing_type",
            "license_count",
            "price_per_license",
            "start_date",
            "end_date",
            "status",
            "is_trial",
            "created_date",
            "last_updated_date",
            "trial_text",
            "notes",
        ]
        extra_kwargs = {
            'plan': {'required': True},
            'billing_type': {'required': True},
        }
