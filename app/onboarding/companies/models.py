import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


class Company(models.Model):
    companyId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core fields
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    # user who created the company
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_companies",
        db_column="created_by_user",
    )

    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    # Onboarding fields
    industry = models.CharField(max_length=120, blank=True, null=True)
    company_size = models.CharField(max_length=120, blank=True, null=True)
    company_email = models.EmailField(blank=True, null=True)
    company_phone = models.CharField(max_length=30, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    domain = models.CharField(max_length=255, blank=True, null=True)
    logo_url = models.CharField(max_length=500, blank=True, null=True)

    # Workspace preferences
    time_zone = models.CharField(max_length=120, default="UTC")
    language = models.CharField(max_length=50, default="en-US")

    # Billing & plan
    plan = models.CharField(max_length=50, default="starter")

    LIFECYCLE_STATES = [
        ("signup", "Signup"),
        ("onboarding", "Onboarding"),
        ("trial", "Trial"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("cancelled", "Cancelled"),
        ("suspended", "Suspended"),
    ]
    lifecycle_status = models.CharField(
        max_length=20, choices=LIFECYCLE_STATES, default="signup"
    )

    billing_email = models.EmailField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)

    discount_percent = models.IntegerField(default=0)
    trial_start_date = models.DateTimeField(blank=True, null=True)
    trial_end_date = models.DateTimeField(blank=True, null=True)
    subscription_renewal_date = models.DateTimeField(blank=True, null=True)

    workspace_limit = models.IntegerField(default=5)
    storage_limit_mb = models.IntegerField(default=500)

    # Product modules (JSON list)
    products = models.JSONField(default=list, blank=True)

    # AI settings
    ai_enabled = models.BooleanField(default=True)
    monthly_ai_quota = models.IntegerField(default=1000)
    ai_persona = models.JSONField(default=dict, blank=True)
    ai_memory_enabled = models.BooleanField(default=False)
    data_sources = models.JSONField(default=list, blank=True)
    ai_config = models.JSONField(default=dict, blank=True)
    security_mode = models.CharField(max_length=50, default="standard")

    # Analytics counters
    total_users = models.IntegerField(default=1)
    active_users_last_30_days = models.IntegerField(default=0)
    ai_interactions_month = models.IntegerField(default=0)
    projects_count = models.IntegerField(default=0)
    tasks_count = models.IntegerField(default=0)
    created_via = models.CharField(max_length=50, default="web")

    # Compliance
    data_retention_days = models.IntegerField(default=365)
    gdpr_consent = models.BooleanField(default=False)
    last_security_review = models.DateTimeField(blank=True, null=True)

    sso_enabled = models.BooleanField(default=False)
    audit_logging_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "companies_company"
        ordering = ["-created_date"]

    def __str__(self):
        return self.name
