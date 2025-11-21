"""
RBAC Models - Role-Based Access Control
World-class implementation following best practices
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from app.core.models.base import CoreBaseModel, SoftDeleteModel
from .constants import (
    PlatformRoles,
    CustomerRoles,
    ModuleRoles,
    Permissions,
    Modules,
    VisibilityLevels,
)


class Role(CoreBaseModel, SoftDeleteModel):
    """
    Defines roles in the system.
    Can be Platform-level, Customer-level, or Module-specific.
    """
    
    ROLE_TYPE_CHOICES = [
        ("platform", "Platform Role"),
        ("customer", "Customer Role"),
        ("module", "Module Role"),
    ]
    
    # Core fields
    name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=100, unique=True, db_index=True)  # e.g., "super_admin", "sales_manager"
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    role_type = models.CharField(max_length=20, choices=ROLE_TYPE_CHOICES, db_index=True)
    module = models.CharField(
        max_length=50,
        choices=[(m.value, m.value) for m in Modules],
        null=True,
        blank=True,
        db_index=True,
        help_text="Module this role belongs to (for module roles)"
    )
    
    # Hierarchy
    hierarchy_level = models.IntegerField(
        default=0,
        help_text="Higher number = more permissions. Used for role comparison."
    )
    
    # Metadata
    is_system_role = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted or modified"
    )
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "rbac_roles"
        ordering = ["role_type", "hierarchy_level", "name"]
        indexes = [
            models.Index(fields=["role_type", "is_active"]),
            models.Index(fields=["module", "is_active"]),
        ]
    
    def __str__(self):
        return f"{self.display_name} ({self.code})"


class Permission(CoreBaseModel):
    """
    Defines granular permissions in the system.
    """
    
    # Core fields
    name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=100, unique=True, db_index=True)  # e.g., "view", "create", "manage"
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Category
    category = models.CharField(
        max_length=50,
        default="general",
        help_text="Permission category: general, crud, admin, ai, etc."
    )
    
    # Metadata
    is_system_permission = models.BooleanField(
        default=False,
        help_text="System permissions cannot be deleted"
    )
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "rbac_permissions"
        ordering = ["category", "name"]
    
    def __str__(self):
        return f"{self.display_name} ({self.code})"


class ModulePermission(CoreBaseModel):
    """
    Maps permissions to products.
    Defines which permissions are available for each product.
    """
    
    module = models.CharField(
        max_length=50,
        choices=[(m.value, m.value) for m in Modules],
        db_index=True
    )
    
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="module_permissions"
    )
    
    is_default = models.BooleanField(
        default=False,
        help_text="Default permission for this module"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "rbac_module_permissions"
        unique_together = [("module", "permission")]
        indexes = [
            models.Index(fields=["module", "is_default"]),
        ]
    
    def __str__(self):
        return f"{self.module} - {self.permission.display_name}"


class RolePermission(CoreBaseModel):
    """
    Maps permissions to roles.
    Defines what permissions each role has.
    """
    
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions"
    )
    
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions"
    )
    
    module = models.CharField(
        max_length=50,
        choices=[(m.value, m.value) for m in Modules],
        null=True,
        blank=True,
        db_index=True,
        help_text="Module context for this permission (optional)"
    )
    
    # Conditions
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional conditions for this permission (e.g., owner_only, team_only)"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "rbac_role_permissions"
        unique_together = [("role", "permission", "module")]
        indexes = [
            models.Index(fields=["role", "module"]),
        ]
    
    def __str__(self):
        module_str = f" ({self.module})" if self.module else ""
        return f"{self.role.display_name} - {self.permission.display_name}{module_str}"


class UserRole(CoreBaseModel, SoftDeleteModel):
    """
    Assigns roles to users.
    Can be company-scoped or module-scoped.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
        db_index=True
    )
    
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles"
    )
    
    # Scope
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="user_roles",
        null=True,
        blank=True,
        db_index=True,
        help_text="Company scope (null for platform roles)"
    )
    
    module = models.CharField(
        max_length=50,
        choices=[(m.value, m.value) for m in Modules],
        null=True,
        blank=True,
        db_index=True,
        help_text="Module scope (for module-specific roles)"
    )
    
    # Assignment metadata
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles"
    )
    
    assigned_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Role expiration (for temporary assignments)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "rbac_user_roles"
        unique_together = [("user", "role", "company", "module")]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["module", "is_active"]),
            models.Index(fields=["expires_at"]),
        ]
    
    def __str__(self):
        scope = f" @ {self.company.name}" if self.company else ""
        module_str = f" [{self.module}]" if self.module else ""
        return f"{self.user.email} - {self.role.display_name}{scope}{module_str}"
    
    def is_expired(self):
        """Check if role assignment has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def is_valid(self):
        """Check if role assignment is valid (active and not expired)."""
        return self.is_active and not self.is_deleted and not self.is_expired()


class RoleInheritance(CoreBaseModel):
    """
    Defines role inheritance relationships.
    Allows roles to inherit permissions from parent roles.
    """
    
    child_role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="parent_inheritances"
    )
    
    parent_role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="child_inheritances"
    )
    
    module = models.CharField(
        max_length=50,
        choices=[(m.value, m.value) for m in Modules],
        null=True,
        blank=True,
        db_index=True,
        help_text="Module context (optional)"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "rbac_role_inheritances"
        unique_together = [("child_role", "parent_role", "module")]
    
    def __str__(self):
        module_str = f" ({self.module})" if self.module else ""
        return f"{self.child_role.display_name} inherits from {self.parent_role.display_name}{module_str}"


class PermissionOverride(CoreBaseModel):
    """
    Allows custom permission overrides for specific users or teams.
    Useful for granting temporary elevated permissions.
    """
    
    OVERRIDE_TYPE_CHOICES = [
        ("user", "User Override"),
        ("team", "Team Override"),
        ("company", "Company Override"),
    ]
    
    override_type = models.CharField(max_length=20, choices=OVERRIDE_TYPE_CHOICES)
    
    # Target
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="permission_overrides"
    )
    
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="permission_overrides"
    )
    
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="permission_overrides"
    )
    
    # Permission details
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="overrides"
    )
    
    module = models.CharField(
        max_length=50,
        choices=[(m.value, m.value) for m in Modules],
        db_index=True
    )
    
    # Override action
    action = models.CharField(
        max_length=20,
        choices=[("grant", "Grant"), ("deny", "Deny")],
        default="grant"
    )
    
    # Validity
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    reason = models.TextField(blank=True, help_text="Reason for override")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_overrides"
    )
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "rbac_permission_overrides"
        indexes = [
            models.Index(fields=["override_type", "is_active"]),
            models.Index(fields=["module", "is_active"]),
            models.Index(fields=["expires_at"]),
        ]
    
    def __str__(self):
        target = self.user.email if self.user else (self.team.name if self.team else self.company.name)
        return f"{self.action.upper()} {self.permission.display_name} for {target} in {self.module}"
    
    def is_expired(self):
        """Check if override has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def is_valid(self):
        """Check if override is valid."""
        return self.is_active and not self.is_expired()

