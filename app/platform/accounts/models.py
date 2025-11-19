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
        PROJECTMANAGER = "ProjectManager"
        SALESMANAGER = "SalesManager"
        SUPPORTMANAGER = "SupportManager"
        MARKETINGMANAGER = "MarketingManager"
        USER = "User"
        PROJECTUSER = "ProjectUser"
        SALESUSER = "SalesUser"
        SUPPORTUser = "SupportUser"
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

    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Security fields
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users_user"
        ordering = ["-created_date"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["email_verified"]),
        ]

    def __str__(self):
        return self.email

    def is_account_locked(self):
        """Check if account is locked due to failed login attempts."""
        if self.account_locked_until:
            from django.utils import timezone
            return timezone.now() < self.account_locked_until
        return False

    def lock_account(self, minutes=30):
        """Lock account for specified minutes."""
        from django.utils import timezone
        from datetime import timedelta
        self.account_locked_until = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=["account_locked_until"])

    def unlock_account(self):
        """Unlock account and reset failed attempts."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=["account_locked_until", "failed_login_attempts"])

    def record_failed_login(self):
        """Record a failed login attempt and lock if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lock_account(minutes=30)
        else:
            self.save(update_fields=["failed_login_attempts"])

    def record_successful_login(self):
        """Reset failed attempts on successful login."""
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.save(update_fields=["failed_login_attempts"])


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


# ================================================
# EMAIL VERIFICATION TOKEN
# ================================================
class EmailVerificationToken(models.Model):
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_token",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    @classmethod
    def create_for_user(cls, user, hours_valid: int = 24):
        """Create email verification token valid for specified hours."""
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=hours_valid),
        )

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.used and timezone.now() <= self.expires_at

    def mark_used(self):
        """Mark token as used."""
        self.used = True
        self.save(update_fields=["used"])

    class Meta:
        db_table = "users_email_verification_tokens"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"EmailVerificationToken({getattr(self.user, 'email', str(self.user))})"


# ================================================
# PASSWORD RESET TOKEN
# ================================================
class PasswordResetToken(models.Model):
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    @classmethod
    def create_for_user(cls, user, hours_valid: int = 1):
        """Create password reset token valid for specified hours."""
        # Invalidate all previous tokens for this user
        cls.objects.filter(user=user, used=False).update(used=True)
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=hours_valid),
        )

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.used and timezone.now() <= self.expires_at

    def mark_used(self):
        """Mark token as used."""
        self.used = True
        self.save(update_fields=["used"])

    class Meta:
        db_table = "users_password_reset_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "used"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"PasswordResetToken({getattr(self.user, 'email', str(self.user))})"
