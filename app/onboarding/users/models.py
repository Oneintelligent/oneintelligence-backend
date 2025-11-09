import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from app.onboarding.companies.models import Company
from app.onboarding.subscriptions.models import Subscriptions  # Import your subscription model

class Users(models.Model):
    class Role(models.TextChoices):
        ADMIN = "Admin"
        MANAGER = "Manager"
        USER = "User"
        GUEST = "Guest"

    class Status(models.TextChoices):
        ACTIVE = "Active"
        INACTIVE = "Inactive"
        SUSPENDED = "Suspended"

    class AuthType(models.TextChoices):
        PASSWORD = "Password"
        OAUTH = "OAuth"
        SSO = "SSO"

    # Unique user identifier
    userId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Personal info
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)

    # ForeignKey to Company
    companyId = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    # Optional fields
    alternate_emails = ArrayField(models.EmailField(), blank=True, default=list)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    team_ids = ArrayField(models.UUIDField(), blank=True, default=list)
    profile_picture_url = models.URLField(blank=True, null=True)
    language_preference = models.CharField(max_length=10, blank=True, default="en-US")
    time_zone = models.CharField(max_length=50, blank=True, default="UTC")
    status = models.CharField(max_length=10, choices=Status.choices, blank=True, default=Status.ACTIVE)

    # Timestamps
    last_login_date = models.DateTimeField(blank=True, null=True)
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    # Settings/preferences
    settings = models.JSONField(blank=True, default=dict)

    # Authentication
    authentication_type = models.CharField(max_length=10, choices=AuthType.choices, blank=True, default=AuthType.PASSWORD)
    two_factor_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.email})"

    # --- Custom properties for related data ---
    
    @property
    def company(self):
        """Return the company object for this user"""
        return self.companyId

    @property
    def subscriptions(self):
        """Return a queryset of subscriptions associated with this user or their company"""
        if self.companyId:
            # Fetch company subscriptions + per-user subscriptions
            return Subscriptions.objects.filter(models.Q(company=self.companyId) | models.Q(user=self))
        return Subscriptions.objects.filter(user=self)
