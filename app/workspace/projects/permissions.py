"""
Projects Module Permissions - RBAC Integration
Enterprise-grade permission checking for Projects module
"""

import logging
from rest_framework.permissions import BasePermission
from django.db.models import Q

from app.platform.rbac.utils import (
    has_module_permission,
    can_view_record,
    can_edit_record,
    can_delete_record,
    is_platform_admin,
)
from app.platform.rbac.constants import Modules, Permissions
from .models import Project, ProjectMember

logger = logging.getLogger(__name__)


def can_view_project(user, project):
    """
    Check if user can view a project using RBAC system.
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Platform admins can view all
    if is_platform_admin(user):
        return True
    
    # Use RBAC system
    can_view = can_view_record(user, project, module=Modules.PROJECTS)
    
    # Additional check: project members can always view
    if not can_view:
        if ProjectMember.objects.filter(project=project, user=user).exists():
            return True
    
    return can_view


def can_edit_project(user, project):
    """
    Check if user can edit a project using RBAC system.
    """
    if not can_view_project(user, project):
        return False
    
    # Platform admins can edit all
    if is_platform_admin(user):
        return True
    
    # Owner can always edit
    if project.owner_id == user.userId:
        return True
    
    # Check member role
    member = ProjectMember.objects.filter(project=project, user=user).first()
    if member and member.role in ["owner", "manager"]:
        return True
    
    # Use RBAC system
    return can_edit_record(user, project, module=Modules.PROJECTS)


def can_delete_project(user, project):
    """
    Check if user can delete a project using RBAC system.
    """
    if not can_view_project(user, project):
        return False
    
    # Platform admins can delete all
    if is_platform_admin(user):
        return True
    
    # Only owner can delete
    if project.owner_id == user.userId:
        return True
    
    # Use RBAC system
    return can_delete_record(user, project, module=Modules.PROJECTS)


class HasProjectPermission(BasePermission):
    """
    DRF permission class for projects module permissions.
    """
    
    def __init__(self, permission: Permissions):
        self.permission = permission
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if is_platform_admin(request.user):
            return True
        
        company = getattr(request.user, 'company', None)
        return has_module_permission(request.user, Modules.PROJECTS, self.permission, company=company)
