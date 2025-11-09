from rest_framework import serializers
from .models import Product, ProductField, CompanyProduct, CompanyProductField


class ProductFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductField
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    fields = ProductFieldSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class CompanyProductFieldSerializer(serializers.ModelSerializer):
    field = ProductFieldSerializer(read_only=True)

    class Meta:
        model = CompanyProductField
        fields = ["id", "company_product", "field", "is_active"]


class CompanyProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    fields = CompanyProductFieldSerializer(many=True, read_only=True)

    class Meta:
        model = CompanyProduct
        fields = ["id", "company", "product", "is_active", "activated_date", "fields"]
