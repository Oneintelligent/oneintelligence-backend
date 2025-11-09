from rest_framework import serializers
from .models import Users
from app.onboarding.companies.models import Company
from app.onboarding.subscriptions.models import Subscriptions


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
        extra_kwargs = {
            'name': {'required': True},
            'created_by_user_id': {'required': True},
        }


class SubscriptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriptions
        fields = '__all__'


class UsersSerializer(serializers.ModelSerializer):
    # Nested serializers for company and subscriptions
    company = CompanySerializer(source='companyId', read_only=True)
    subscriptions = SubscriptionsSerializer(many=True, read_only=True)

    class Meta:
        model = Users
        fields = [
            'userId',
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
            'status',
            'company',
            'subscriptions',
            'alternate_emails',
            'profile_picture_url',
            'language_preference',
            'time_zone',
            'last_login_date',
            'created_date',
            'last_updated_date',
        ]
        read_only_fields = ['userId', 'created_date', 'last_updated_date', 'company', 'subscriptions']
