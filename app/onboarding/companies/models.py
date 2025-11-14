import uuid
from datetime import timedelta

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class Company(models.Model):
    """Company / Workspace model with lifecycle tracking for onboarding & billing."""

    # ------------------------
    # Lifecycle / Account state
    # ------------------------
    class LifecycleStatus(models.TextChoices):
        SIGNED_UP = "SignedUp", "Signed Up"          # user signed up but NOT created a workspace
        ONBOARDING = "Onboarding", "Onboarding"      # workspace created, steps in progress
        ACTIVE = "Active", "Active"                  # fully activated & live
        TRIAL_EXPIRED = "TrialExpired", "Trial Expired"
        SUSPENDED = "Suspended", "Suspended"
        CANCELLED = "Cancelled", "Cancelled"
        ARCHIVED = "Archived", "Archived"

    # ------------------------
    # Company size options
    # ------------------------
    COMPANY_SIZE_CHOICES = [
        ("0 to 10", "0 to 10"),
        ("10 to 50", "10 to 50"),
        ("50 to 100", "50 to 100"),
        ("100 and above", "100 and above"),
    ]

    # ------------------------
    # Primary identifiers
    # ------------------------
    companyId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_by_user_id = models.UUIDField(blank=False)  # reference to User.userId (stored as UUID)

    # ------------------------
    # Business info
    # ------------------------
    discount_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Optional company-level discount (0-100)",
    )
    description = models.TextField(blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    company_size = models.CharField(
        max_length=20,
        choices=COMPANY_SIZE_CHOICES,
        blank=True,
        null=True,
    )

    # ------------------------
    # Contact info
    # ------------------------
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Tags (lowercase enforced)
    tags = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Lowercased string tags",
    )

    # ------------------------
    # Related IDs (non-FK for decoupled micro-modules)
    # ------------------------
    user_list = ArrayField(
        models.UUIDField(),
        blank=True,
        default=list,
        help_text="List of user UUIDs belonging to this company",
    )
    subscription_ids = ArrayField(
        models.UUIDField(),
        blank=True,
        default=list,
        help_text="List of subscription UUIDs",
    )
    product_ids = ArrayField(
        models.UUIDField(),
        blank=True,
        default=list,
        help_text="List of product UUIDs/modules enabled",
    )

    # ------------------------
    # Payment + Lifecycle
    # ------------------------
    payment_status = models.CharField(
        max_length=10,
        choices=[("Pending", "Pending"), ("Paid", "Paid")],
        default="Pending",
        help_text="Simple payment flag (external billing system recommended)",
    )

    lifecycle_status = models.CharField(
        max_length=20,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.SIGNED_UP,
        help_text="Customer lifecycle status",
    )

    # Onboarding progress for UI (0-100)
    onboarding_progress = models.PositiveIntegerField(
        default=0,
        help_text="0–100 progress indicator for onboarding UI",
    )

    # Timestamps for each lifecycle transition
    onboarding_started_at = models.DateTimeField(blank=True, null=True)
    activated_at = models.DateTimeField(blank=True, null=True)
    trial_expired_at = models.DateTimeField(blank=True, null=True)
    suspended_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)

    # Arbitrary metadata
    settings = models.JSONField(blank=True, default=dict)

    # Metadata
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies_company"
        indexes = [
            models.Index(fields=["lifecycle_status"]),
            models.Index(fields=["created_date"]),
        ]
        ordering = ["-created_date"]

    def __str__(self):
        return self.name

    # ------------------------
    # Derived properties
    # ------------------------
    @property
    def total_users(self):
        return len(self.user_list or [])

    # ------------------------
    # Utility helpers (state machine)
    # ------------------------
    def start_onboarding(self):
        if self.lifecycle_status != self.LifecycleStatus.ONBOARDING:
            self.lifecycle_status = self.LifecycleStatus.ONBOARDING
            self.onboarding_started_at = self.onboarding_started_at or timezone.now()
            self.save(update_fields=[
                "lifecycle_status", "onboarding_started_at", "last_updated_date"
            ])

    def mark_activated(self):
        self.lifecycle_status = self.LifecycleStatus.ACTIVE
        self.activated_at = timezone.now()
        self.onboarding_progress = 100
        self.save(update_fields=[
            "lifecycle_status", "activated_at", "onboarding_progress", "last_updated_date"
        ])

    def mark_trial_expired(self):
        self.lifecycle_status = self.LifecycleStatus.TRIAL_EXPIRED
        self.trial_expired_at = timezone.now()
        self.save(update_fields=[
            "lifecycle_status", "trial_expired_at", "last_updated_date"
        ])

    def mark_suspended(self, reason=None):
        self.lifecycle_status = self.LifecycleStatus.SUSPENDED
        self.suspended_at = timezone.now()
        if reason:
            s = self.settings or {}
            s["suspend_reason"] = reason
            self.settings = s
            self.save(update_fields=[
                "lifecycle_status", "suspended_at", "settings", "last_updated_date"
            ])
        else:
            self.save(update_fields=[
                "lifecycle_status", "suspended_at", "last_updated_date"
            ])

    def mark_cancelled(self):
        self.lifecycle_status = self.LifecycleStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.save(update_fields=[
            "lifecycle_status", "cancelled_at", "last_updated_date"
        ])

    def mark_archived(self):
        self.lifecycle_status = self.LifecycleStatus.ARCHIVED
        self.archived_at = timezone.now()
        self.save(update_fields=[
            "lifecycle_status", "archived_at", "last_updated_date"
        ])

    # ------------------------
    # Data consistency
    # ------------------------
    def clean(self):
        if self.tags:
            self.tags = [t.lower() for t in self.tags]
        if self.discount_percentage < 0:
            self.discount_percentage = 0
        if self.discount_percentage > 100:
            self.discount_percentage = 100

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
