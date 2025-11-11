import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone


class Subscriptions(models.Model):
    class PlanChoices(models.TextChoices):
        PRO = "Pro"
        MAX = "Max"
        ULTRA_MAX = "Ultra Max"

    class BillingType(models.TextChoices):
        MONTHLY = "Monthly"
        YEARLY = "Yearly"

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active"
        INACTIVE = "Inactive"
        CANCELLED = "Cancelled"

    subscriptionId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 🔹 Store plain UUID references instead of ForeignKeys
    companyId = models.UUIDField(blank=True, null=True, help_text="UUID of the company")
    userId = models.UUIDField(blank=True, null=True, help_text="UUID of the user who created or owns the subscription")

    plan = models.CharField(max_length=20, choices=PlanChoices.choices)
    billing_type = models.CharField(max_length=10, choices=BillingType.choices, default=BillingType.MONTHLY)
    license_count = models.PositiveIntegerField(default=1)
    price_per_license = models.PositiveIntegerField()
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.INACTIVE)
    is_trial = models.BooleanField(default=False)
    trial_text = models.CharField(max_length=50, blank=True, null=True)
    notes = models.CharField(max_length=50, blank=True, null=True)

    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions_subscription'

    def __str__(self):
        return f"{self.plan} ({self.billing_type})"

    def save(self, *args, **kwargs):
        # Auto price handling
        plan_prices = {
            "Pro": {"Monthly": 1200, "Yearly": 12000},
            "Max": {"Monthly": 3000, "Yearly": 33000},
            "Ultra Max": {"Monthly": 6000, "Yearly": 66000},
        }

        # Handle 90-day free trial for Max plan
        if self.plan == "Max" and not self.pk and self.is_trial:
            self.price_per_license = 0
            self.start_date = timezone.now()
            self.end_date = self.start_date + timedelta(days=90)
            self.status = self.StatusChoices.ACTIVE
        else:
            self.price_per_license = plan_prices[self.plan][self.billing_type]

        super().save(*args, **kwargs)
