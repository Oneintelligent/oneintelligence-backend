import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings

# ---------------------------------------------------------
# Visibility Levels
# ---------------------------------------------------------
VISIBILITY_CHOICES = [
    ("owner", "Owner Only"),
    ("team", "Team"),
    ("company", "Company"),
    ("shared", "Shared"),
]


# =========================================================
#  ACCOUNT MODEL
# =========================================================
class Account(models.Model):
    account_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        db_column="companyId",
        related_name="sales_accounts"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="accounts_owned"
    )

    team = models.ForeignKey(
        "teams.Team",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="accounts"
    )

    # ----------- Core Fields ----------
    name = models.CharField(max_length=255)
    primary_email = models.EmailField(blank=True, null=True)
    primary_phone = models.CharField(max_length=50, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=32, default="active")

    # AI / Intelligent Fields
    health_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    metadata = models.JSONField(default=dict, blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="team")
    shared_with = models.JSONField(default=list, blank=True)

    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_accounts"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["company", "name"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["team"]),
        ]

    def __str__(self):
        return self.name or "Unnamed Account"


# =========================================================
#  LEAD MODEL
# =========================================================
class Lead(models.Model):
    lead_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        db_column="companyId",
        related_name="sales_leads"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="leads_owned"
    )

    team = models.ForeignKey(
        "teams.Team",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="leads"
    )

    account = models.ForeignKey(
        "sales.Account",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="accountId",
        related_name="leads"
    )

    # ----------- Lead details ----------
    first_name = models.CharField(max_length=120, blank=True, null=True)
    last_name = models.CharField(max_length=120, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=64, blank=True, null=True)

    status = models.CharField(max_length=32, default="new")
    source = models.CharField(max_length=64, default="manual")

    # ----------- Visibility ----------
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="team")
    shared_with = models.JSONField(default=list)

    # ----------- Metadata ----------
    tags = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)

    # ----------- AI Scoring ----------
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ai_reasons = models.JSONField(default=list)

    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_leads"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["team"]),
        ]

    def __str__(self):
        label = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return label or self.email or "Unnamed Lead"


# =========================================================
#  OPPORTUNITY MODEL
# =========================================================
class Opportunity(models.Model):
    opp_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        db_column="companyId",
        related_name="sales_opportunities"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="opps_owned"
    )

    team = models.ForeignKey(
        "teams.Team",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="opps"
    )

    lead = models.ForeignKey(
        Lead,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="opportunities"
    )

    account = models.ForeignKey(
        Account,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="opportunities"
    )

    # ----------- Core Fields ----------
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    currency = models.CharField(max_length=10, default="INR")
    stage = models.CharField(max_length=64, default="prospect")

    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="team")
    shared_with = models.JSONField(default=list)

    probability = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expected_close_date = models.DateField(null=True, blank=True)

    metadata = models.JSONField(default=dict)

    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_opportunities"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "stage"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["team"]),
        ]

    def __str__(self):
        return self.title or "Opportunity"


# =========================================================
#  ACTIVITY MODEL
# =========================================================
class Activity(models.Model):
    activity_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        db_column="companyId",
        related_name="sales_activities"
    )

    team = models.ForeignKey(
        "teams.Team",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="activities"
    )

    # entity_type: lead | opportunity | account
    entity_type = models.CharField(max_length=20)
    entity_id = models.UUIDField()

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="activities"
    )

    kind = models.CharField(max_length=32)
    body = models.TextField(blank=True, null=True)

    occurred_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "sales_activities"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["company", "entity_type"]),
            models.Index(fields=["actor"]),
        ]

    def __str__(self):
        return f"{self.kind} - {self.entity_type}"
