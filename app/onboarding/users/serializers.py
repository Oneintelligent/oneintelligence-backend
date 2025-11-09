from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Users
from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import CompanySerializer
from app.onboarding.subscriptions.models import Subscriptions
from app.onboarding.subscriptions.serializers import SubscriptionsSerializer

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    companyId = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True
    )

    # Nested serializers for read-only responses
    company = CompanySerializer(source='companyId', read_only=True)
    subscriptions = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = '__all__'

    def get_subscriptions(self, obj):
        # Return all subscriptions for this user
        user_subs = Subscriptions.objects.filter(user=obj)
        return SubscriptionsSerializer(user_subs, many=True).data

    def validate(self, data):
        email = data.get('email')
        company = data.get('companyId')

        if not email:
            raise serializers.ValidationError({"email": "Email is required for all users."})

        if not company:
            required_fields = ['first_name', 'last_name', 'phone', 'password']
            missing_fields = [f for f in required_fields if not data.get(f)]
            if missing_fields:
                raise serializers.ValidationError(
                    {f: f"{f} is required when company is not provided." for f in missing_fields}
                )
        return data

    def create(self, validated_data):
        if validated_data.get('password'):
            validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('password'):
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)
