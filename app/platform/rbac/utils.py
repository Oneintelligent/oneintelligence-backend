"""
RBAC Utility Functions
Permission checking and role management utilities
"""

import logging
from typing import Optional, List, Set, Union
from django.db.models import Q
from django.conf import settings

logger = logging.getLogger(__name__)
from .models import (
    Role,
    Permission,
    UserRole,
    RolePermission,
    PermissionOverride,
    RoleInheritance,
)
from .constants import (
    PlatformRoles,
    CustomerRoles,
    ModuleRoles,
    Permissions,
    Modules,
    VisibilityLevels,
    ROLE_HIERARCHY,
)
from app.platform.products.models import CompanyModule, ModuleDefinition


def get_user_roles(user, company=None, module=None) -> List[Role]:
    """
    Get all active roles for a user.
    
    Args:
        user: User instance
        company: Optional company to scope roles
        module: Optional module to scope roles
    
    Returns:
        List of Role instances
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return []
    
    query = Q(user=user, is_active=True, is_deleted=False)
    
    if company:
        query &= Q(company=company) | Q(company__isnull=True)
    else:
        query &= Q(company__isnull=True)
    
    if module:
        query &= Q(module=module) | Q(module__isnull=True)
    
    user_roles = UserRole.objects.filter(query).select_related('role')
    
    # Filter expired roles
    valid_roles = [ur.role for ur in user_roles if ur.is_valid()]
    
    return valid_roles


def _get_inherited_permissions(role, module=None, visited=None) -> Set[str]:
    """
    Recursively get all permissions from a role and its parent roles.
    Handles circular dependencies.
    
    Args:
        role: Role instance
        module: Optional module to scope permissions
        visited: Set of visited role IDs to prevent circular references
    
    Returns:
        Set of permission codes
    """
    if visited is None:
        visited = set()
    
    # Prevent circular references
    if role.id in visited:
        return set()
    visited.add(role.id)
    
    permissions = set()
    
    # Get direct permissions for this role
    query = Q(role=role, role__is_active=True)
    if module:
        query &= Q(module=module) | Q(module__isnull=True)
    
    role_perms = RolePermission.objects.filter(query).select_related('permission')
    permissions.update([rp.permission.code for rp in role_perms])
    
    # Get inherited permissions (recursive)
    inheritances = RoleInheritance.objects.filter(
        child_role=role
    ).select_related('parent_role')
    
    for inheritance in inheritances:
        parent_role = inheritance.parent_role
        
        # Recursively get permissions from parent
        parent_perms = _get_inherited_permissions(parent_role, module=module, visited=visited.copy())
        permissions.update(parent_perms)
        
        # Also get direct permissions from parent
        parent_query = Q(role=parent_role, role__is_active=True)
        if module:
            parent_query &= Q(module=module) | Q(module__isnull=True)
        
        parent_direct_perms = RolePermission.objects.filter(parent_query).select_related('permission')
        permissions.update([rp.permission.code for rp in parent_direct_perms])
    
    return permissions


def get_user_permissions(user, company=None, module=None) -> Set[str]:
    """
    Get all permissions for a user.
    Includes permissions from roles and recursively from parent roles.
    
    Args:
        user: User instance
        company: Optional company to scope permissions
        module: Optional module to scope permissions
    
    Returns:
        Set of permission codes
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return set()
    
    permissions = set()
    
    # Get user roles
    roles = get_user_roles(user, company=company, module=module)
    
    # Get permissions from roles (with recursive inheritance)
    for role in roles:
        role_perms = _get_inherited_permissions(role, module=module)
        permissions.update(role_perms)
    
    # Apply permission overrides
    override_query = Q(is_active=True)
    if user:
        override_query &= Q(user=user)
    if company:
        override_query &= Q(company=company) | Q(company__isnull=True)
    if module:
        override_query &= Q(module=module)
    
    overrides = PermissionOverride.objects.filter(override_query)
    
    for override in overrides:
        if override.is_valid():
            if override.action == "grant":
                permissions.add(override.permission.code)
            elif override.action == "deny":
                permissions.discard(override.permission.code)
    
    return permissions


def has_permission(user, permission: Union[str, Permissions], company=None, module=None) -> bool:
    """
    Check if user has a specific permission.
    If module is provided, validates all three levels: company module enabled, roles, and permissions.
    
    Args:
        user: User instance
        permission: Permission code or Permissions enum
        company: Optional company context
        module: Optional module context (if provided, validates module enabled status)
    
    Returns:
        True if user has permission, False otherwise
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Convert enum to string if needed
    perm_code = permission.value if isinstance(permission, Permissions) else permission
    
    # Platform admins have all permissions
    if is_platform_admin(user):
        return True
    
    # If module is provided, use has_module_permission which validates all three levels
    if module:
        return has_module_permission(user, module, permission, company=company)
    
    # Get company context if not provided
    if not company:
        company = getattr(user, 'company', None)
    
    # Get user permissions
    user_perms = get_user_permissions(user, company=company, module=module)
    
    return perm_code in user_perms


def is_module_enabled_for_company(module: Union[str, Modules], company) -> bool:
    """
    Check if a module is enabled for a company.
    
    This validates Level 1: Company-level module access.
    
    Args:
        module: Module code or Modules enum
        company: Company instance or company ID
    
    Returns:
        True if module is enabled for company, False otherwise
    """
    if not company:
        return False
    
    # Get company ID
    company_id = getattr(company, 'companyId', None) or getattr(company, 'id', None) or company
    
    # Convert module to code
    module_code = module.value if isinstance(module, Modules) else module
    
    # Check if module is enabled for company
    try:
        module_def = ModuleDefinition.objects.get(code=module_code, is_active=True)
        company_module = CompanyModule.objects.filter(
            company_id=company_id,
            module=module_def,
            enabled=True,
            is_active=True
        ).first()
        
        return company_module is not None
    except (ModuleDefinition.DoesNotExist, Exception):
        return False


def validate_module_access(user, module: Union[str, Modules], permission: Union[str, Permissions] = None, company=None) -> dict:
    """
    Comprehensive validation of module access across all three levels:
    1. Company module enabled (CompanyModule.enabled = True)
    2. User has role/permission for the module
    3. User access (handled by RBAC)
    
    Args:
        user: User instance
        module: Module code or Modules enum
        permission: Optional permission to check (if None, only checks module enabled)
        company: Optional company context (defaults to user.company)
    
    Returns:
        dict with validation results:
        {
            'has_access': bool,
            'module_enabled': bool,
            'has_permission': bool,
            'has_role': bool,
            'reason': str  # Reason for denial if has_access is False
        }
    """
    result = {
        'has_access': False,
        'module_enabled': False,
        'has_permission': False,
        'has_role': False,
        'reason': None
    }
    
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        result['reason'] = 'User not authenticated'
        return result
    
    # Platform admins bypass all checks
    if is_platform_admin(user):
        result['has_access'] = True
        result['module_enabled'] = True
        result['has_permission'] = True
        result['has_role'] = True
        return result
    
    # Get company context
    if not company:
        company = getattr(user, 'company', None)
    
    if not company:
        result['reason'] = 'User not associated with a company'
        return result
    
    module_code = module.value if isinstance(module, Modules) else module
    
    # Level 1: Check if module is enabled for company
    result['module_enabled'] = is_module_enabled_for_company(module_code, company)
    if not result['module_enabled']:
        result['reason'] = f"Module '{module_code}' is not enabled for company"
        return result
    
    # Level 2: Check user roles
    user_roles = get_user_roles(user, company=company, module=module_code)
    result['has_role'] = len(user_roles) > 0
    
    # Level 3: Check permission if provided
    if permission:
        result['has_permission'] = has_permission(user, permission, company=company, module=module_code)
        if not result['has_permission']:
            perm_code = permission.value if isinstance(permission, Permissions) else permission
            result['reason'] = f"User does not have '{perm_code}' permission for module '{module_code}'"
            return result
    
    # All checks passed
    result['has_access'] = True
    return result


def has_module_permission(user, module: Union[str, Modules], permission: Union[str, Permissions], company=None) -> bool:
    """
    Check if user has a specific permission in a module.
    Validates all three levels:
    1. Company module enabled (CompanyModule.enabled = True)
    2. User has role/permission for the module
    3. User access (handled by RBAC)
    
    Args:
        user: User instance
        module: Module code or Modules enum
        permission: Permission code or Permissions enum
        company: Optional company context (defaults to user.company)
    
    Returns:
        True if user has permission AND module is enabled for company, False otherwise
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Platform admins bypass all checks
    if is_platform_admin(user):
        return True
    
    # Get company context
    if not company:
        company = getattr(user, 'company', None)
    
    if not company:
        return False
    
    module_code = module.value if isinstance(module, Modules) else module
    
    # Level 1: Check if module is enabled for company
    if not is_module_enabled_for_company(module_code, company):
        logger.debug(
            f"Module access denied: Module '{module_code}' not enabled for company "
            f"{getattr(company, 'name', company)} (ID: {getattr(company, 'companyId', company)})"
        )
        return False
    
    # Level 2 & 3: Check user roles and permissions (RBAC)
    has_perm = has_permission(user, permission, company=company, module=module_code)
    
    if not has_perm:
        logger.debug(
            f"Module permission denied: User {user.email} does not have '{permission}' "
            f"permission for module '{module_code}' in company {getattr(company, 'name', company)}"
        )
    
    return has_perm


def has_role(user, role: Union[str, Role], company=None, module=None) -> bool:
    """
    Check if user has a specific role.
    
    Args:
        user: User instance
        role: Role code, Role enum, or Role instance
        company: Optional company context
        module: Optional module context
    
    Returns:
        True if user has role, False otherwise
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Convert to role code
    if isinstance(role, Role):
        role_code = role.code
    elif isinstance(role, (PlatformRoles, CustomerRoles, ModuleRoles)):
        role_code = role.value
    else:
        role_code = role
    
    # Get user roles
    user_roles = get_user_roles(user, company=company, module=module)
    
    return any(ur.code == role_code for ur in user_roles)


def can_view_record(user, record, module: Optional[Union[str, Modules]] = None) -> bool:
    """
    Check if user can view a record based on visibility and permissions.
    Validates all three levels: company module enabled, roles, and permissions.
    
    Args:
        user: User instance
        record: Record instance (must have visibility, owner, company attributes)
        module: Optional module context (REQUIRED for workspace modules)
    
    Returns:
        True if user can view record, False otherwise
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Platform admins can view all
    if is_platform_admin(user):
        return True
    
    # Get record attributes
    record_company = getattr(record, 'company_id', None) or getattr(record, 'company', None)
    user_company = getattr(user, 'company_id', None) or getattr(user, 'company', None)
    
    # SuperAdmin can view all records in their company
    if is_super_admin(user, company=user_company):
        if record_company and user_company and str(record_company) == str(user_company):
            return True
    
    # Must be in same company
    if record_company and user_company and str(record_company) != str(user_company):
        return False
    
    # If module is specified, validate module access first (Level 1: Company module enabled)
    if module:
        if not has_module_permission(user, module, Permissions.VIEW, company=user_company):
            logger.debug(
                f"Record view denied: Module '{module.value if isinstance(module, Modules) else module}' "
                f"not accessible for user {user.email} in company {getattr(user_company, 'name', user_company)}"
            )
            return False
    
    # Check visibility
    visibility = getattr(record, 'visibility', VisibilityLevels.OWNER.value)
    
    # Owner can always view
    owner_id = None
    if hasattr(record, 'owner_id'):
        owner_id = getattr(record, 'owner_id', None)
    elif hasattr(record, 'owner'):
        owner_obj = getattr(record, 'owner', None)
        if owner_obj:
            owner_id = getattr(owner_obj, 'userId', None) or getattr(owner_obj, 'id', None)
    
    user_id = getattr(user, 'userId', None) or getattr(user, 'id', None)
    
    if owner_id and user_id and str(owner_id) == str(user_id):
        return True
    
    # Check visibility levels
    if visibility == VisibilityLevels.OWNER.value:
        return False
    
    if visibility == VisibilityLevels.COMPANY.value:
        # Check if user has view permission for this module (already validated above if module provided)
        if module:
            return True  # Already validated by has_module_permission above
        return True
    
    if visibility == VisibilityLevels.TEAM.value:
        record_team = None
        if hasattr(record, 'team_id'):
            record_team = getattr(record, 'team_id', None)
        elif hasattr(record, 'team'):
            team_obj = getattr(record, 'team', None)
            if team_obj:
                record_team = getattr(team_obj, 'team_id', None) or getattr(team_obj, 'id', None)
        
        user_team = getattr(user, 'team_id', None) or (getattr(user, 'team', None) and getattr(user.team, 'team_id', None) or getattr(user.team, 'id', None))
        
        # If record has no team assigned, fall back to company visibility
        if not record_team:
            # Treat as company visibility if no team is set
            if module:
                return True  # Already validated by has_module_permission above
            return True
        
        # If record has a team, check if user is in that team
        if record_team and user_team and str(record_team) == str(user_team):
            return True
    
    if visibility == VisibilityLevels.SHARED.value:
        shared_with = getattr(record, 'shared_with', []) or []
        if user_id and str(user_id) in [str(x) for x in shared_with]:
            return True
    
    # If module was provided, access was already validated above
    if module:
        return True
    
    return False


def can_edit_record(user, record, module: Optional[Union[str, Modules]] = None) -> bool:
    """
    Check if user can edit a record.
    Validates all three levels: company module enabled, roles, and permissions.
    
    Args:
        user: User instance
        record: Record instance
        module: Optional module context (REQUIRED for workspace modules)
    
    Returns:
        True if user can edit record, False otherwise
    """
    if not can_view_record(user, record, module=module):
        return False
    
    # Platform admins can edit all
    if is_platform_admin(user):
        return True
    
    # Owner can always edit
    owner_id = getattr(record, 'owner_id', None) or (getattr(record, 'owner', None) and getattr(record.owner, 'userId', None) or getattr(record.owner, 'id', None))
    user_id = getattr(user, 'userId', None) or getattr(user, 'id', None)
    
    if owner_id and user_id and str(owner_id) == str(user_id):
        return True
    
    # Check update permission (validates all three levels)
    record_company = getattr(record, 'company_id', None) or getattr(record, 'company', None)
    if module:
        return has_module_permission(user, module, Permissions.UPDATE, company=record_company)
    
    return has_permission(user, Permissions.UPDATE, company=record_company, module=module)


def can_delete_record(user, record, module: Optional[Union[str, Modules]] = None) -> bool:
    """
    Check if user can delete a record.
    Validates all three levels: company module enabled, roles, and permissions.
    
    Args:
        user: User instance
        record: Record instance
        module: Optional module context (REQUIRED for workspace modules)
    
    Returns:
        True if user can delete record, False otherwise
    """
    if not can_view_record(user, record, module=module):
        return False
    
    # Platform admins can delete all
    if is_platform_admin(user):
        return True
    
    # Owner can always delete
    owner_id = getattr(record, 'owner_id', None) or (getattr(record, 'owner', None) and getattr(record.owner, 'userId', None) or getattr(record.owner, 'id', None))
    user_id = getattr(user, 'userId', None) or getattr(user, 'id', None)
    
    if owner_id and user_id and str(owner_id) == str(user_id):
        return True
    
    # Check delete permission (validates all three levels)
    record_company = getattr(record, 'company_id', None) or getattr(record, 'company', None)
    if module:
        return has_module_permission(user, module, Permissions.DELETE, company=record_company)
    
    return has_permission(user, Permissions.DELETE, company=record_company, module=module)


def can_manage_record(user, record, module: Optional[Union[str, Modules]] = None) -> bool:
    """
    Check if user can manage (full control) a record.
    Validates all three levels: company module enabled, roles, and permissions.
    
    Args:
        user: User instance
        record: Record instance
        module: Optional module context (REQUIRED for workspace modules)
    
    Returns:
        True if user can manage record, False otherwise
    """
    if not can_view_record(user, record, module=module):
        return False
    
    # Platform admins can manage all
    if is_platform_admin(user):
        return True
    
    # Check manage permission (validates all three levels)
    record_company = getattr(record, 'company_id', None) or getattr(record, 'company', None)
    if module:
        return has_module_permission(user, module, Permissions.MANAGE, company=record_company)
    
    return has_permission(user, Permissions.MANAGE, company=record_company, module=module)


def is_platform_admin(user) -> bool:
    """Check if user is a platform admin."""
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    return has_role(user, PlatformRoles.PLATFORM_ADMIN)


def is_super_admin(user, company=None) -> bool:
    """Check if user is a super admin (owner) in a company."""
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Check RBAC role first
    if has_role(user, CustomerRoles.SUPER_ADMIN, company=company):
        return True
    
    # Fallback: Check legacy role field (for users not yet migrated to RBAC)
    legacy_role = getattr(user, 'role', None)
    if legacy_role and legacy_role.lower() in ['superadmin', 'super_admin']:
        return True
    
    return False


def is_company_admin(user, company=None) -> bool:
    """Check if user is a company admin."""
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    return has_role(user, CustomerRoles.ADMIN, company=company) or has_role(user, CustomerRoles.SUPER_ADMIN, company=company)


def get_role_hierarchy_level(role: Union[str, Role]) -> int:
    """Get hierarchy level for a role."""
    if isinstance(role, Role):
        return role.hierarchy_level
    
    if isinstance(role, (PlatformRoles, CustomerRoles, ModuleRoles)):
        return ROLE_HIERARCHY.get(role, 0)
    
    # Try to find in hierarchy
    return ROLE_HIERARCHY.get(role, 0)


def compare_roles(role1: Union[str, Role], role2: Union[str, Role]) -> int:
    """
    Compare two roles by hierarchy.
    
    Returns:
        -1 if role1 < role2
        0 if role1 == role2
        1 if role1 > role2
    """
    level1 = get_role_hierarchy_level(role1)
    level2 = get_role_hierarchy_level(role2)
    
    if level1 < level2:
        return -1
    elif level1 > level2:
        return 1
    return 0


def role_inherits_from(child_role: Union[str, Role], parent_role: Union[str, Role], module=None) -> bool:
    """
    Check if a role inherits from another role (directly or indirectly).
    
    Args:
        child_role: Child role to check
        parent_role: Parent role to check against
        module: Optional module context
    
    Returns:
        True if child_role inherits from parent_role
    """
    from .models import Role
    
    # Convert to Role instances if needed
    if isinstance(child_role, str):
        try:
            child_role = Role.objects.get(code=child_role, is_active=True)
        except Role.DoesNotExist:
            return False
    
    if isinstance(parent_role, str):
        try:
            parent_role = Role.objects.get(code=parent_role, is_active=True)
        except Role.DoesNotExist:
            return False
    
    # Same role
    if child_role.id == parent_role.id:
        return True
    
    # Check direct inheritance
    direct_inheritance = RoleInheritance.objects.filter(
        child_role=child_role,
        parent_role=parent_role
    )
    if module:
        direct_inheritance = direct_inheritance.filter(
            Q(module=module) | Q(module__isnull=True)
        )
    
    if direct_inheritance.exists():
        return True
    
    # Check indirect inheritance (recursive)
    all_parents = RoleInheritance.objects.filter(
        child_role=child_role
    ).select_related('parent_role')
    
    if module:
        all_parents = all_parents.filter(Q(module=module) | Q(module__isnull=True))
    
    for inheritance in all_parents:
        if role_inherits_from(inheritance.parent_role, parent_role, module=module):
            return True
    
    return False


def get_role_ancestors(role: Union[str, Role], module=None) -> List[Role]:
    """
    Get all ancestor roles (parent, grandparent, etc.) for a role.
    
    Args:
        role: Role to get ancestors for
        module: Optional module context
    
    Returns:
        List of ancestor Role instances
    """
    from .models import Role
    
    # Convert to Role instance if needed
    if isinstance(role, str):
        try:
            role = Role.objects.get(code=role, is_active=True)
        except Role.DoesNotExist:
            return []
    
    ancestors = []
    visited = set()
    
    def _collect_ancestors(current_role, visited_set):
        if current_role.id in visited_set:
            return
        visited_set.add(current_role.id)
        
        inheritances = RoleInheritance.objects.filter(
            child_role=current_role
        ).select_related('parent_role')
        
        if module:
            inheritances = inheritances.filter(Q(module=module) | Q(module__isnull=True))
        
        for inheritance in inheritances:
            parent = inheritance.parent_role
            if parent.id not in visited_set:
                ancestors.append(parent)
                _collect_ancestors(parent, visited_set)
    
    _collect_ancestors(role, visited)
    return ancestors

