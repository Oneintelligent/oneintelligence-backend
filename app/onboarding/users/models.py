import uuid
from django.db import models
from django.utils import timezone


class User(models.Model):
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

    # Primary identifier
    userId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # New plain string fields for references
    companyId = models.CharField(max_length=100, blank=True, null=True)
    subscriptionId = models.CharField(max_length=100, blank=True, null=True)

    # User details
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)

    # Profile & settings
    role = models.CharField(max_length=10, choices=Role.choices, blank=True, default=Role.USER)
    profile_picture_url = models.URLField(blank=True, null=True)
    language_preference = models.CharField(max_length=10, blank=True, default="en-US")
    time_zone = models.CharField(max_length=50, blank=True, default="UTC")
    status = models.CharField(max_length=10, choices=Status.choices, blank=True, default=Status.ACTIVE)

    # Metadata
    last_login_date = models.DateTimeField(blank=True, null=True)
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    # Settings/preferences
    settings = models.JSONField(blank=True, default=dict)

    # Authentication
    authentication_type = models.CharField(max_length=10, choices=AuthType.choices, blank=True, default=AuthType.PASSWORD)
    two_factor_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.email or 'No Email'})"

    class Meta:
        db_table = "users_user"  # ✅ Ensures table name matches expectations
        verbose_name = "User"
        verbose_name_plural = "Users"
