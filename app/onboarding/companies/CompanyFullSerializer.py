from rest_framework import serializers
from app.onboarding.companies.models import Company
from app.onboarding.users.models import User
from app.subscriptions.models import Subscriptions, SubscriptionPlan
from app.products.models import Product


class ProductLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["productId", "code", "name", "description"]


class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["userId", "email", "first_name", "last_name", "role", "status"]


class SubscriptionLiteSerializer(serializers.ModelSerializer):
    plan = serializers.CharField(source="plan.name")

    class Meta:
        model = Subscriptions
        fields = [
            "subscriptionId",
            "plan",
            "billing_type",
            "license_count",
            "is_trial",
            "start_date",
            "end_date",
            "status",
        ]


class CompanyFullSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "companyId",
            "name",
            "description",
            "industry",
            "company_size",
            "email",
            "phone",
            "tags",
            "discount_percentage",
            "status",
            "country",
            "website",
            
            "products",
            "subscription",
            "team",
        ]

    def get_products(self, obj):
        if not obj.product_ids:
            return []
        qs = Product.objects.filter(productId__in=obj.product_ids)
        return ProductLiteSerializer(qs, many=True).data

    def get_subscription(self, obj):
        if not obj.subscription_ids:
            return None
        sub = Subscriptions.objects.filter(subscriptionId=obj.subscription_ids[0]).first()
        return SubscriptionLiteSerializer(sub).data if sub else None

    def get_team(self, obj):
        if not obj.user_list:
            return []
        qs = User.objects.filter(userId__in=obj.user_list)
        return UserLiteSerializer(qs, many=True).data
