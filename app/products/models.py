# app/products/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

class Product(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        INACTIVE = 'Inactive', 'Inactive'
        ARCHIVED = 'Archived', 'Archived'

    productId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True)   # e.g. "PROJECTS", "CRM"
    description = models.TextField(blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    base_price = models.PositiveIntegerField(default=0)
    billing_cycle = models.CharField(max_length=20, default="Monthly")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name
