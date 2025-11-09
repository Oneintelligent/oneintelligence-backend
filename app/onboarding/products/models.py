import uuid
from django.db import models
from django.utils import timezone
from app.onboarding.companies.models import Company

class Product(models.Model):
    productId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductField(models.Model):
    fieldId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=100)
    data_type = models.CharField(max_length=50, default="string")
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class CompanyProduct(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="company_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="company_products")
    is_active = models.BooleanField(default=False)
    activated_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("company", "product")

    def __str__(self):
        return f"{self.company.name} - {self.product.name} ({'Active' if self.is_active else 'Inactive'})"


class CompanyProductField(models.Model):
    company_product = models.ForeignKey(CompanyProduct, on_delete=models.CASCADE, related_name="fields")
    field = models.ForeignKey(ProductField, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ("company_product", "field")

    def __str__(self):
        return f"{self.company_product.company.name} - {self.field.product.name} - {self.field.name} ({'Active' if self.is_active else 'Inactive'})"
