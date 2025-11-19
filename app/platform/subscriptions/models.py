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
        MAX = "MaxPro", "Max Pro"
        ULTRA = "Ultra", "Ultra"

    class StatusChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    # ---- Core Plan Info ----
    name = models.CharField(
        max_length=32,
        choices=PlanChoices.choices,
        unique=False  # You will create 3 entries per seat pack
    )

    # Example: {"1": 999, "3": 1999, "5": 2999, ...}
    base_prices = models.JSONField(default=dict)

    # multipliers: Pro=1, MaxPro=1.5, Ultra=4
    multiplier = models.FloatField(default=1.0)

    # Generic feature toggles
    features = models.JSONField(default=list)

    # Trials
    has_trial = models.BooleanField(default=False)
    trial_days = models.PositiveIntegerField(default=90)

    # Discount that applies globally to plan
    global_discount_percentage = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"

    def __str__(self):
        return f"{self.name}"

    # -------------------------
    # Price Calculator (core)
    # -------------------------
    def get_pack_price(self, seats: int) -> int:
        """Returns the final pack price for the given seat count."""
        seat_str = str(seats)
        if seat_str not in self.base_prices:
            raise ValueError(f"Seat pack '{seat_str}' not defined for plan {self.name}")

        base_price = self.base_prices[seat_str]
        final = base_price * self.multiplier
        return int(final)


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
            from app.platform.companies.models import Company
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
            from app.platform.accounts.models import User
            user = User.objects.filter(userId=self.userId).first()
            return getattr(user, "discount_percentage", 0) or 0
        except Exception:
            return 0


    # -------------------------
    # Main Price Calculation
    # -------------------------
    def save(self, *args, **kwargs):
        """
        Updated save() with pack-based pricing:
        - Uses SubscriptionPlan.get_pack_price()
        - Applies discounts (plan, company, user)
        - Applies trial override
        """

        # 1️⃣ Get pack price based on selected license_count (seat pack)
        # Example: plan.get_pack_price(10) returns:
        #   Pro: 4999
        #   MaxPro: 7499
        #   Ultra: 19999

        try:
            base_price = self.plan.get_pack_price(self.license_count)
            self.base_price_per_license = 0  # pack-based, not per-seat
        except Exception:
            # fallback
            base_price = 0

        
        # 2️⃣ Apply discounts (highest wins)
        plan_discount = int(self.plan.global_discount_percentage or 0)
        company_discount = self._get_company_discount()
        user_discount = self._get_user_discount()

        applied_discount = max(plan_discount, company_discount, user_discount)
        self.applied_discount = applied_discount

        discounted_price = base_price * (100 - applied_discount) / 100
        self.final_total_price = int(discounted_price)

        # 3️⃣ Trial override
        if self.is_trial:
            self.final_total_price = 0
            if not self.end_date:
                days = self.plan.trial_days or 90
                self.end_date = timezone.now() + timedelta(days=days)
            self.status = self.StatusChoices.ACTIVE

        super().save(*args, **kwargs)
