import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class Company(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        INACTIVE = 'Inactive', 'Inactive'
        ARCHIVED = 'Archived', 'Archived'

    COMPANY_SIZE_CHOICES = [
        '0 to 10',
        '10 to 50',
        '50 to 100',
        '100 and above'
    ]

    # Primary key
    companyId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Required
    name = models.CharField(max_length=255)
    created_by_user_id = models.UUIDField(blank=False)

    # Optional descriptive fields
    discount_percentage = models.PositiveIntegerField(default=0, help_text="Optional company-level discount")
    description = models.TextField(blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    company_size = models.CharField(
        max_length=20,
        choices=[(s, s) for s in COMPANY_SIZE_CHOICES],
        blank=True,
        null=True
    )

    # Contact info
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=50), blank=True, default=list)

    # Users, subscriptions, products — all plain UUID arrays (no FK)
    user_list = ArrayField(
        models.UUIDField(),
        blank=True,
        default=list,
        help_text="List of user UUIDs belonging to this company"
    )
    subscription_ids = ArrayField(
        models.UUIDField(),
        blank=True,
        default=list,
        help_text="List of subscription UUIDs associated with this company"
    )
    product_ids = ArrayField(
        models.UUIDField(),
        blank=True,
        default=list,
        help_text="List of product UUIDs associated with this company"
    )

    # Status and payment info
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.INACTIVE
    )
    payment_status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Paid', 'Paid')],
        default='Pending'
    )

    # Metadata
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'companies_company'

    def __str__(self):
        return self.name
