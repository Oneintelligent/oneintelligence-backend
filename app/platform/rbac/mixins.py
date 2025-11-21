"""
RBAC Mixins for Enterprise-Grade Permission Management
Provides reusable mixins for ViewSets and views
"""

import logging
from typing import Optional
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from .utils import (
    has_permission,
    has_module_permission,
    can_view_record,
    can_edit_record,
    can_delete_record,
    can_manage_record,
    is_platform_admin,
    is_super_admin,
    is_company_admin,
    get_user_permissions,
)
from .constants import Permissions, Modules, VisibilityLevels

logger = logging.getLogger(__name__)


class RBACPermissionMixin:
    """
    Base mixin for RBAC permission checking.
    Provides enterprise-grade permission utilities.
    """
    
    # Override these in subclasses
    module: Optional[Modules] = None
    permission_required_for_list: Optional[Permissions] = Permissions.VIEW
    permission_required_for_create: Optional[Permissions] = Permissions.CREATE
    permission_required_for_update: Optional[Permissions] = Permissions.UPDATE
    permission_required_for_delete: Optional[Permissions] = Permissions.DELETE
    permission_required_for_retrieve: Optional[Permissions] = Permissions.VIEW
    
    def get_module(self) -> Optional[Modules]:
        """Get the module for this view. Override in subclasses."""
        return self.module
    
    def check_permission(self, user, permission: Permissions, company=None) -> bool:
        """
        Check if user has permission.
        Enterprise-grade with proper logging.
        SuperAdmin and PlatformAdmin bypass all permission checks.
        """
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            logger.warning(f"Permission check failed: User not authenticated")
            return False
        
        module = self.get_module()
        
        # Platform admins bypass all checks
        if is_platform_admin(user):
            return True
        
        # SuperAdmin bypasses all permission checks for their company
        if not company:
            company = getattr(user, 'company', None)
        if is_super_admin(user, company=company):
            return True
        
        if module:
            has_perm = has_module_permission(user, module, permission, company=company)
        else:
            has_perm = has_permission(user, permission, company=company, module=module)
        
        if not has_perm:
            logger.info(
                f"Permission denied: user={user.email}, permission={permission.value}, "
                f"module={module.value if module else None}, company={company.name if company else None}"
            )
        
        return has_perm
    
    def check_record_access(self, user, record, action: str = "view") -> bool:
        """
        Check if user can access a record.
        Enterprise-grade with proper logging.
        SuperAdmin and PlatformAdmin bypass all record access checks.
        """
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            return False
        
        # Platform admins bypass all checks
        if is_platform_admin(user):
            return True
        
        # SuperAdmin bypasses all checks for their company
        company = getattr(user, 'company', None)
        if is_super_admin(user, company=company):
            return True
        
        module = self.get_module()
        
        if action == "view":
            can_access = can_view_record(user, record, module=module)
        elif action == "edit":
            can_access = can_edit_record(user, record, module=module)
        elif action == "delete":
            can_access = can_delete_record(user, record, module=module)
        elif action == "manage":
            can_access = can_manage_record(user, record, module=module)
        else:
            can_access = can_view_record(user, record, module=module)
        
        if not can_access:
            logger.info(
                f"Record access denied: user={user.email}, action={action}, "
                f"record_id={getattr(record, 'id', None)}, module={module.value if module else None}"
            )
        
        return can_access
    
    def filter_queryset_by_permissions(self, queryset: QuerySet, user) -> QuerySet:
        """
        Filter queryset based on user permissions and visibility.
        Enterprise-grade filtering with proper optimization.
        """
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            return queryset.none()
        
        if is_platform_admin(user):
            return queryset
        
        # Get user company
        company = getattr(user, 'company', None)
        company_id = getattr(user, 'company_id', None) or (company.id if company else None)
        
        if not company_id:
            return queryset.none()
        
        # Base filter: same company
        conditions = Q(company_id=company_id)
        
        # Owner can always see their records
        user_id = getattr(user, 'userId', None) or getattr(user, 'id', None)
        if user_id:
            conditions = conditions & (
                Q(owner_id=user_id) |
                Q(visibility=VisibilityLevels.COMPANY.value) |
                Q(visibility=VisibilityLevels.TEAM.value, team_id=getattr(user, 'team_id', None)) |
                Q(visibility=VisibilityLevels.SHARED.value, shared_with__contains=[str(user_id)])
            )
        
        # Check if user has view permission for company-wide visibility
        module = self.get_module()
        if module and has_module_permission(user, module, Permissions.VIEW, company=company):
            # User can see all company records
            return queryset.filter(company_id=company_id)
        
        # Apply visibility-based filtering
        return queryset.filter(conditions).distinct()
    
    def get_permission_denied_response(self, message: str = "Permission denied") -> Response:
        """Standard permission denied response."""
        from app.utils.response import api_response
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            status="failure",
            data={},
            error_code="PERMISSION_DENIED",
            error_message=message,
        )


class RBACViewSetMixin(RBACPermissionMixin):
    """
    Mixin for ViewSets with RBAC integration.
    Provides automatic permission checking for standard actions.
    """
    
    def get_queryset(self):
        """
        Override to filter queryset by permissions.
        """
        queryset = super().get_queryset()
        return self.filter_queryset_by_permissions(queryset, self.request.user)
    
    def list(self, request, *args, **kwargs):
        """List action with permission check."""
        if not self.check_permission(request.user, self.permission_required_for_list):
            return self.get_permission_denied_response("You don't have permission to view this list")
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve action with permission check."""
        if not self.check_permission(request.user, self.permission_required_for_retrieve):
            return self.get_permission_denied_response("You don't have permission to view this record")
        
        obj = self.get_object()
        if not self.check_record_access(request.user, obj, action="view"):
            return self.get_permission_denied_response("You don't have access to this record")
        
        return super().retrieve(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Create action with permission check."""
        if not self.check_permission(request.user, self.permission_required_for_create):
            return self.get_permission_denied_response("You don't have permission to create records")
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update action with permission check."""
        if not self.check_permission(request.user, self.permission_required_for_update):
            return self.get_permission_denied_response("You don't have permission to update records")
        
        obj = self.get_object()
        if not self.check_record_access(request.user, obj, action="edit"):
            return self.get_permission_denied_response("You don't have permission to edit this record")
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update action with permission check."""
        if not self.check_permission(request.user, self.permission_required_for_update):
            return self.get_permission_denied_response("You don't have permission to update records")
        
        obj = self.get_object()
        if not self.check_record_access(request.user, obj, action="edit"):
            return self.get_permission_denied_response("You don't have permission to edit this record")
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Destroy action with permission check."""
        if not self.check_permission(request.user, self.permission_required_for_delete):
            return self.get_permission_denied_response("You don't have permission to delete records")
        
        obj = self.get_object()
        if not self.check_record_access(request.user, obj, action="delete"):
            return self.get_permission_denied_response("You don't have permission to delete this record")
        
        return super().destroy(request, *args, **kwargs)


class RBACQuerySetMixin:
    """
    Mixin for filtering querysets based on RBAC permissions.
    Can be used with any view or manager.
    """
    
    @staticmethod
    def filter_by_user_permissions(queryset: QuerySet, user, module: Optional[Modules] = None) -> QuerySet:
        """
        Filter queryset based on user permissions.
        Enterprise-grade with proper optimization.
        """
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            return queryset.none()
        
        if is_platform_admin(user):
            return queryset
        
        # Get user company
        company = getattr(user, 'company', None)
        company_id = getattr(user, 'company_id', None) or (company.id if company else None)
        
        if not company_id:
            return queryset.none()
        
        # Base filter: same company
        conditions = Q(company_id=company_id)
        
        # Owner can always see their records
        user_id = getattr(user, 'userId', None) or getattr(user, 'id', None)
        if user_id:
            owner_condition = Q(owner_id=user_id)
            
            # Company visibility
            company_visibility = Q(visibility=VisibilityLevels.COMPANY.value)
            
            # Team visibility
            team_id = getattr(user, 'team_id', None)
            team_visibility = Q()
            if team_id:
                team_visibility = Q(visibility=VisibilityLevels.TEAM.value, team_id=team_id)
            
            # Shared visibility
            shared_visibility = Q(visibility=VisibilityLevels.SHARED.value, shared_with__contains=[str(user_id)])
            
            conditions = conditions & (
                owner_condition |
                company_visibility |
                team_visibility |
                shared_visibility
            )
        
        # Check if user has view permission for company-wide visibility
        if module and has_module_permission(user, module, Permissions.VIEW, company=company):
            # User can see all company records
            return queryset.filter(company_id=company_id)
        
        # Apply visibility-based filtering
        return queryset.filter(conditions).distinct()

