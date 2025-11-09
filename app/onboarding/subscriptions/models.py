import uuid
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.conf import settings
from app.onboarding.companies.models import Company

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
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="Company associated with the subscription"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        blank=True,
        null=True,
        help_text="Optional: assign subscription to a specific user"
    )
    plan = models.CharField(max_length=20, choices=PlanChoices.choices)
    billing_type = models.CharField(max_length=10, choices=BillingType.choices, default=BillingType.MONTHLY)
    license_count = models.PositiveIntegerField(default=1)
    price_per_license = models.PositiveIntegerField()  # automatically set based on plan + billing_type
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.INACTIVE)
    is_trial = models.BooleanField(default=False)  # Track trial subscriptions
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        user_part = f" - {self.user.email}" if self.user else ""
        return f"{self.company.name}{user_part} - {self.plan} ({self.billing_type})"

    def save(self, *args, **kwargs):
        plan_prices = {
            "Pro": {"Monthly": 1200, "Yearly": 12000},
            "Max": {"Monthly": 3000, "Yearly": 33000},
            "Ultra Max": {"Monthly": 6000, "Yearly": 66000},
        }

        # Handle 90-day free trial for Max plan on new records
        if self.plan == "Max" and not self.pk and self.is_trial:
            self.price_per_license = 0
            self.start_date = timezone.now()
            self.end_date = self.start_date + timedelta(days=90)
            self.status = self.StatusChoices.ACTIVE
        else:
            self.price_per_license = plan_prices[self.plan][self.billing_type]

        if not self.company:
            raise ValueError("A subscription must belong to a company.")

        super().save(*args, **kwargs)
