from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User


# class UserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, required=False, allow_blank=True)

#     class Meta:
#         model = User
#         fields = '__all__'
#         extra_kwargs = {f: {'required': False, 'allow_null': True, 'allow_blank': True} for f in fields}

#     def create(self, validated_data):
#         if validated_data.get('password'):
#             validated_data['password'] = make_password(validated_data['password'])
#         return super().create(validated_data)

#     def update(self, instance, validated_data):
#         if validated_data.get('password'):
#             validated_data['password'] = make_password(validated_data['password'])
#         return super().update(instance, validated_data)


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