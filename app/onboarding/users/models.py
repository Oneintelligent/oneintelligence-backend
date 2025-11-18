import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.utils import timezone
from django.conf import settings


# ================================================
# USER MANAGER
# ================================================
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email).lower().strip()
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.PLATFORMADMIN)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)

        return self._create_user(email, password, **extra_fields)


# ================================================
# USER MODEL
# ================================================
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
        PENDING = "Pending"
        SUSPENDED = "Suspended"

    userId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
        db_column="companyId",
    )

    # Team reference (for Sales, Support, Projects)
    team = models.ForeignKey(
    "teams.Team",
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="members",
    db_column="teamId"
    )

    # Map .id to userId for DRF/django consistency
    @property
    def id(self):
        return self.userId

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


    # Profile fields
    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    email = models.EmailField(unique=True)  # VARCHAR + functional index
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Roles / permissions
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    profile_picture_url = models.CharField(max_length=1000, blank=True, null=True)
    language_preference = models.CharField(max_length=20, default="en-US", blank=True)
    time_zone = models.CharField(max_length=50, default="UTC", blank=True)

    discount_percentage = models.IntegerField(default=0)

    last_login = models.DateTimeField(blank=True, null=True)
    created_date = models.DateTimeField(default=timezone.now)
    last_updated_date = models.DateTimeField(auto_now=True)

    preferences = models.JSONField(default=dict, blank=True)

    # Django fields
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Manager
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users_user"
        ordering = ["-created_date"]

    def __str__(self):
        return self.email


# -------------------------
# Invite Token
# -------------------------
class InviteToken(models.Model):
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Use settings.AUTH_USER_MODEL to avoid hard import
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invite_token",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def create_for_user(cls, user, days_valid: int = 7):
        return cls.objects.create(user=user, expires_at=timezone.now() + timedelta(days=days_valid))

    def is_valid(self) -> bool:
        return timezone.now() <= self.expires_at

    def __str__(self) -> str:
        return f"InviteToken({getattr(self.user, 'email', str(self.user))})"


# class InviteToken(models.Model):
#     token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.OneToOneField(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="invite_token"
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     expires_at = models.DateTimeField()

#     @classmethod
#     def create_for_user(cls, user, days_valid=7):
#         return cls.objects.create(
#             user=user,
#             expires_at=timezone.now() + timedelta(days=days_valid),
#         )

#     def is_valid(self):
#         return timezone.now() <= self.expires_at

#     def __str__(self):
#         return f"InviteToken({self.user.email})"
