from __future__ import annotations
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

from app.onboarding.companies.models import Company

# import Company model from your companies app
from app.onboarding.companies.models import Company


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("role", "PlatformAdmin")
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Single user model. Company is a proper FK (companyId db column) so we can easily return
    user + company with select_related('company').
    """
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
        PENDING = "Pending"          # <-- ADDED
        SUSPENDED = "Suspended"

    userId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="companyId",
        related_name="users",
    )

    # Basic profile fields
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Role / status
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    profile_picture_url = models.URLField(blank=True, null=True)
    language_preference = models.CharField(max_length=20, default="en-US", blank=True)
    time_zone = models.CharField(max_length=50, default="UTC", blank=True)

    discount_percentage = models.PositiveIntegerField(default=0)

    # Metadata
    last_login_date = models.DateTimeField(blank=True, null=True)
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    settings = models.JSONField(default=dict, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users_user"
        ordering = ["-created_date"]

    def __str__(self):
        return f"{self.email}"



class InviteToken(models.Model):
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invite_token")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def create_for_user(cls, user, days_valid: int = 7):
        return cls.objects.create(user=user, expires_at=timezone.now() + timedelta(days=days_valid))

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def __str__(self):
        return f"InviteToken({self.user.email})"
