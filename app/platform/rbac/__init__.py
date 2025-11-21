"""
Role-Based Access Control (RBAC) System
World-class RBAC implementation following best practices from Atlassian, Freshworks, and Microsoft.
"""

# Lazy imports to avoid circular dependencies
# Models are imported when needed, not at module level

from .constants import (
    PlatformRoles,
    CustomerRoles,
    ModuleRoles,
    Permissions,
    Modules,
    VisibilityLevels,
)

__all__ = [
    # Constants (safe to import)
    "PlatformRoles",
    "CustomerRoles",
    "ModuleRoles",
    "Permissions",
    "Modules",
    "VisibilityLevels",
]

# Models and utils are available but imported lazily to avoid circular imports
# Import them when needed:
#   from app.platform.rbac.models import Role, Permission, UserRole, RoleInheritance
#   from app.platform.rbac.utils import (
#       has_permission, has_role,
#       role_inherits_from, get_role_ancestors,
#       get_role_hierarchy_level, compare_roles
#   )
#   from app.platform.rbac.permissions import HasPermission, CanViewRecord

