"""
Sales Module Permissions - RBAC Integration
Enterprise-grade permission checking for Sales module
"""

import logging
from rest_framework.permissions import BasePermission
from django.conf import settings

from app.platform.rbac.utils import (
    has_module_permission,
    can_view_record,
    can_edit_record,
    can_delete_record,
    is_platform_admin,
)
from app.platform.rbac.constants import Modules, Permissions

logger = logging.getLogger(__name__)


def _get_user_id(user):
    """Get user ID supporting both userId and id attributes."""
    return str(getattr(user, "userId", None) or getattr(user, "id", None))


def is_sales_role(user):
    """
    Check if user has a sales-related role using RBAC.
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    company = getattr(user, 'company', None)
    return has_module_permission(user, Modules.SALES, Permissions.VIEW, company=company)


def can_view_sales_record(user, record):
    """
    Check if user can view a sales record.
    Uses new RBAC system with backward compatibility.
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Platform admins can view all
    if is_platform_admin(user):
        return True
    
    # Use RBAC system
    return can_view_record(user, record, module=Modules.SALES)


def can_edit_sales_record(user, record):
    """Check if user can edit a sales record."""
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    if is_platform_admin(user):
        return True
    
    return can_edit_record(user, record, module=Modules.SALES)


def can_delete_sales_record(user, record):
    """Check if user can delete a sales record."""
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    if is_platform_admin(user):
        return True
    
    return can_delete_record(user, record, module=Modules.SALES)


class IsSalesRecordVisible(BasePermission):
    """
    DRF permission class for sales record visibility.
    Uses RBAC system.
    """
    
    def has_object_permission(self, request, view, obj):
        return can_view_sales_record(request.user, obj)
    
    def has_permission(self, request, view):
        return getattr(request.user, "is_authenticated", False)


class HasSalesPermission(BasePermission):
    """
    DRF permission class for sales module permissions.
    """
    
    def __init__(self, permission: Permissions):
        self.permission = permission
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None)
        return has_module_permission(request.user, Modules.SALES, self.permission, company=company)
