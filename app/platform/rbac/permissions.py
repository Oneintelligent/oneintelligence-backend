"""
DRF Permission Classes for RBAC
Easy integration with Django REST Framework
"""

from rest_framework import permissions
from .utils import (
    has_permission,
    has_module_permission,
    has_role,
    can_view_record,
    can_edit_record,
    can_delete_record,
    can_manage_record,
    is_platform_admin,
    is_super_admin,
    is_company_admin,
)
from .constants import Permissions, Modules, PlatformRoles, CustomerRoles


class HasPermission(permissions.BasePermission):
    """
    DRF permission class that checks if user has a specific permission.
    
    Usage:
        permission_classes = [HasPermission(Permissions.VIEW, Modules.SALES)]
    """
    
    def __init__(self, permission, module=None, company_required=True):
        self.permission = permission
        self.module = module
        self.company_required = company_required
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Platform admins have all permissions
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None) if self.company_required else None
        
        if self.module:
            return has_module_permission(request.user, self.module, self.permission, company=company)
        else:
            return has_permission(request.user, self.permission, company=company)


class HasModulePermission(permissions.BasePermission):
    """
    DRF permission class for module-specific permissions.
    
    Usage:
        permission_classes = [HasModulePermission(Modules.SALES, Permissions.CREATE)]
    """
    
    def __init__(self, module, permission):
        self.module = module
        self.permission = permission
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None)
        return has_module_permission(request.user, self.module, self.permission, company=company)


class HasRole(permissions.BasePermission):
    """
    DRF permission class that checks if user has a specific role.
    
    Usage:
        permission_classes = [HasRole(CustomerRoles.SUPER_ADMIN)]
    """
    
    def __init__(self, role, company_required=True):
        self.role = role
        self.company_required = company_required
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None) if self.company_required else None
        return has_role(request.user, self.role, company=company)


class IsPlatformAdmin(permissions.BasePermission):
    """Check if user is a platform admin."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_platform_admin(request.user)


class IsSuperAdmin(permissions.BasePermission):
    """Check if user is a super admin (owner) in their company."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None)
        return is_super_admin(request.user, company=company)


class IsCompanyAdmin(permissions.BasePermission):
    """Check if user is a company admin or super admin."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None)
        return is_company_admin(request.user, company=company)


class CanViewRecord(permissions.BasePermission):
    """
    Object-level permission to check if user can view a record.
    
    Usage:
        permission_classes = [CanViewRecord(Modules.SALES)]
    """
    
    def __init__(self, module=None):
        self.module = module
    
    def has_permission(self, request, view):
        # List/create endpoints - check basic authentication
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if is_platform_admin(request.user):
            return True
        
        return can_view_record(request.user, obj, module=self.module)


class CanEditRecord(permissions.BasePermission):
    """
    Object-level permission to check if user can edit a record.
    
    Usage:
        permission_classes = [CanEditRecord(Modules.SALES)]
    """
    
    def __init__(self, module=None):
        self.module = module
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if is_platform_admin(request.user):
            return True
        
        return can_edit_record(request.user, obj, module=self.module)


class CanDeleteRecord(permissions.BasePermission):
    """
    Object-level permission to check if user can delete a record.
    
    Usage:
        permission_classes = [CanDeleteRecord(Modules.SALES)]
    """
    
    def __init__(self, module=None):
        self.module = module
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if is_platform_admin(request.user):
            return True
        
        return can_delete_record(request.user, obj, module=self.module)


class CanManageRecord(permissions.BasePermission):
    """
    Object-level permission to check if user can manage (full control) a record.
    
    Usage:
        permission_classes = [CanManageRecord(Modules.SALES)]
    """
    
    def __init__(self, module=None):
        self.module = module
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if is_platform_admin(request.user):
            return True
        
        return can_manage_record(request.user, obj, module=self.module)


class ReadOnlyOrHasPermission(permissions.BasePermission):
    """
    Allows read-only access, or write access if user has specific permission.
    
    Usage:
        permission_classes = [ReadOnlyOrHasPermission(Permissions.CREATE, Modules.SALES)]
    """
    
    def __init__(self, permission, module=None):
        self.permission = permission
        self.module = module
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        # Read-only methods
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write methods require permission
        company = getattr(request.user, 'company', None)
        if self.module:
            return has_module_permission(request.user, self.module, self.permission, company=company)
        else:
            return has_permission(request.user, self.permission, company=company)

