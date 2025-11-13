import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone


# ------------------------------------------------------------------------------------------------
#   SubscriptionPlan (clean, consistent, stable)
# ------------------------------------------------------------------------------------------------
class SubscriptionPlan(models.Model):

    class PlanChoices(models.TextChoices):
        PRO = "Pro", "Pro"
        MAX = "Max", "Pro Max"
        ULTRA = "Ultra", "Ultra"

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    # Core plan details
    name = models.CharField(max_length=32, choices=PlanChoices.choices, unique=True)
    monthly_price = models.PositiveIntegerField()
    yearly_price = models.PositiveIntegerField()

    # ✔ NEW — enable/disable trial at plan level
    has_trial = models.BooleanField(default=False)

    # ✔ NEW — trial duration (default 90 days)
    trial_days = models.PositiveIntegerField(default=90)
    # Optional discount applies globally to this plan
    global_discount_percentage = models.PositiveIntegerField(default=0)

    # Allow enabling/disabling plan in UI
    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

    # Pricing UI features
    features = models.JSONField(default=list)

    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"    # ⚡ CLEAN TABLE NAME

    def __str__(self):
        return self.name


# ------------------------------------------------------------------------------------------------
#   Subscriptions (company purchases a plan)
# ------------------------------------------------------------------------------------------------
class Subscriptions(models.Model):

    class BillingType(models.TextChoices):
        MONTHLY = "Monthly", "Monthly"
        YEARLY = "Yearly", "Yearly"

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"
        CANCELLED = "Cancelled", "Cancelled"

    subscriptionId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Links
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")

    companyId = models.UUIDField(null=True, blank=True)
    userId = models.UUIDField(null=True, blank=True)

    billing_type = models.CharField(max_length=10, choices=BillingType.choices, default=BillingType.MONTHLY)
    license_count = models.PositiveIntegerField(default=1)

    # Computed pricing fields
    base_price_per_license = models.PositiveIntegerField(default=0)
    final_price_per_license = models.PositiveIntegerField(default=0)
    final_total_price = models.PositiveIntegerField(default=0)
    applied_discount = models.PositiveIntegerField(default=0)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)

    status = models.CharField(max_length=15, choices=StatusChoices.choices, default=StatusChoices.INACTIVE)

    is_trial = models.BooleanField(default=False)
    trial_text = models.CharField(max_length=120, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions"       # ⚡ CLEAN TABLE NAME

    def __str__(self):
        return f"{self.plan.name} | {self.license_count} seats | {self.billing_type}"


    # ---------------------------
    # Helper: Get company discount
    # ---------------------------
    def _get_company_discount(self):
        if not self.companyId:
            return 0

        try:
            from app.onboarding.companies.models import Company
            company = Company.objects.filter(companyId=self.companyId).first()
            return getattr(company, "discount_percentage", 0) or 0
        except Exception:
            return 0

    # ------------------------
    # Helper: Get user discount
    # ------------------------
    def _get_user_discount(self):
        if not self.userId:
            return 0

        try:
            from app.onboarding.users.models import User
            user = User.objects.filter(userId=self.userId).first()
            return getattr(user, "discount_percentage", 0) or 0
        except Exception:
            return 0


    # -------------------------
    # Main Price Calculation
    # -------------------------
    def save(self, *args, **kwargs):

        # 1️⃣ Base price per license
        base_price = (
            self.plan.monthly_price
            if self.billing_type == self.BillingType.MONTHLY
            else self.plan.yearly_price
        )
        self.base_price_per_license = base_price

        # 2️⃣ Get discounts
        plan_discount = int(self.plan.global_discount_percentage or 0)
        company_discount = self._get_company_discount()
        user_discount = self._get_user_discount()

        # Highest wins
        applied_discount = max(plan_discount, company_discount, user_discount)
        self.applied_discount = applied_discount

        # 3️⃣ Apply discount
        discounted_price = base_price * (100 - applied_discount) / 100
        self.final_price_per_license = int(round(discounted_price))

        # 4️⃣ Multiply by seat count
        self.final_total_price = self.final_price_per_license * (self.license_count or 1)

        # 5️⃣ Trial override
        if self.is_trial:
            self.final_price_per_license = 0
            self.final_total_price = 0
            if not self.end_date:
                self.end_date = timezone.now() + timedelta(days=90)
            self.status = self.StatusChoices.ACTIVE

        super().save(*args, **kwargs)
