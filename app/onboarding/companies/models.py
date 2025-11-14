import uuid
from django.db import models
from django.utils import timezone


class Company(models.Model):
    companyId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)

    address = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    created_by_user = models.UUIDField(blank=False)

    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies_company"
        ordering = ["-created_date"]

    def __str__(self):
        return self.name
