"""
Tasks Module Permissions - RBAC Integration
Enterprise-grade permission checking for Tasks module
"""

import logging
from rest_framework.permissions import BasePermission

from app.platform.rbac.utils import (
    has_module_permission,
    can_view_record,
    can_edit_record,
    can_delete_record,
    is_platform_admin,
)
from app.platform.rbac.constants import Modules, Permissions
from .models import Task

logger = logging.getLogger(__name__)


def can_view_task(user, task):
    """
    Check if user can view a task using RBAC system.
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Platform admins can view all
    if is_platform_admin(user):
        return True
    
    # Use RBAC system
    return can_view_record(user, task, module=Modules.TASKS)


def can_edit_task(user, task):
    """
    Check if user can edit a task using RBAC system.
    """
    if not can_view_task(user, task):
        return False
    
    # Platform admins can edit all
    if is_platform_admin(user):
        return True
    
    # Owner or assignee can edit
    if task.owner_id == user.userId or task.assignee_id == user.userId:
        return True
    
    # Use RBAC system
    return can_edit_record(user, task, module=Modules.TASKS)


def can_delete_task(user, task):
    """
    Check if user can delete a task using RBAC system.
    """
    if not can_view_task(user, task):
        return False
    
    # Platform admins can delete all
    if is_platform_admin(user):
        return True
    
    # Only owner can delete
    if task.owner_id == user.userId:
        return True
    
    # Use RBAC system
    return can_delete_record(user, task, module=Modules.TASKS)


class HasTaskPermission(BasePermission):
    """
    DRF permission class for tasks module permissions.
    """
    
    def __init__(self, permission: Permissions):
        self.permission = permission
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None)
        return has_module_permission(request.user, Modules.TASKS, self.permission, company=company)
