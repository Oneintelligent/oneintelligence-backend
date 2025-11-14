import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    """Custom user manager without is_staff / is_superuser logic."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # You can optionally control what makes a "superuser" in your system.
        # For API-only projects, you usually don’t need special privileges.
        return self.create_user(email, password, **extra_fields)



class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        PLATFORMADMIN = "PlatformAdmin"
        SUPERADMIN = "SuperAdmin"
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
    email = models.EmailField(blank=True, null=True, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)

    # Profile & settings
    role = models.CharField(max_length=20, choices=Role.choices, blank=True, default=Role.USER)
    profile_picture_url = models.URLField(blank=True, null=True)
    language_preference = models.CharField(max_length=10, blank=True, default="en-US")
    time_zone = models.CharField(max_length=50, blank=True, default="UTC")
    status = models.CharField(max_length=10, choices=Status.choices, blank=True, default=Status.ACTIVE)

    #discount
    discount_percentage = models.PositiveIntegerField(default=0, help_text="Optional user-level discount")

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

    @property
    def id(self):
        return self.userId
    
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []



