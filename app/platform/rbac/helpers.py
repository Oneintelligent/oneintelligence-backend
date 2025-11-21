"""
RBAC Helper Functions
Utility functions for role assignment and management
"""

import logging
from typing import Optional
from django.db import transaction
from django.conf import settings

from .models import Role, UserRole
from .constants import CustomerRoles, ModuleRoles, PlatformRoles
from .utils import get_user_roles

logger = logging.getLogger(__name__)


def assign_role_to_user(user, role_code: str, company=None, module=None, assigned_by=None):
    """
    Assign a role to a user using RBAC system.
    Creates UserRole entry.
    
    Args:
        user: User instance
        role_code: Role code (e.g., "super_admin", "sales_manager")
        company: Optional company for scoping
        module: Optional module for scoping
        assigned_by: User who assigned this role
    
    Returns:
        UserRole instance
    """
    try:
        # Get role from database
        role = Role.objects.filter(code=role_code, is_active=True).first()
        if not role:
            logger.warning(f"Role not found: {role_code}")
            return None
        
        # Create or update UserRole
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            company=company,
            module=module,
            defaults={
                'assigned_by': assigned_by,
                'is_active': True,
            }
        )
        
        if not created:
            # Update existing role assignment
            user_role.is_active = True
            user_role.assigned_by = assigned_by
            user_role.save()
        
        logger.info(f"Assigned role {role_code} to user {user.email}")
        return user_role
        
    except Exception as e:
        logger.exception(f"Error assigning role {role_code} to user {user.email}: {e}")
        return None


def assign_super_admin_role(user, company, assigned_by=None):
    """
    Assign Super Admin role to a user for a company.
    This is typically done when a user creates a company.
    """
    return assign_role_to_user(
        user=user,
        role_code=CustomerRoles.SUPER_ADMIN.value,
        company=company,
        assigned_by=assigned_by or user
    )


def assign_admin_role(user, company, assigned_by=None):
    """
    Assign Admin role to a user for a company.
    """
    return assign_role_to_user(
        user=user,
        role_code=CustomerRoles.ADMIN.value,
        company=company,
        assigned_by=assigned_by or user
    )


def assign_member_role(user, company, assigned_by=None):
    """
    Assign Member role to a user for a company.
    """
    return assign_role_to_user(
        user=user,
        role_code=CustomerRoles.MEMBER.value,
        company=company,
        assigned_by=assigned_by or user
    )


def assign_module_role(user, role_code: str, company, module: str, assigned_by=None):
    """
    Assign a module-specific role to a user.
    
    Args:
        user: User instance
        role_code: Module role code (e.g., "sales_manager", "project_manager")
        company: Company for scoping
        module: Module name (e.g., "sales", "projects")
        assigned_by: User who assigned this role
    """
    return assign_role_to_user(
        user=user,
        role_code=role_code,
        company=company,
        module=module,
        assigned_by=assigned_by
    )


def get_user_primary_role(user, company=None):
    """
    Get the primary role for a user (highest hierarchy level).
    Useful for display purposes.
    
    Args:
        user: User instance
        company: Optional company for scoping
    
    Returns:
        Role instance or None
    """
    if not user:
        return None
    
    roles = get_user_roles(user, company=company)
    if not roles:
        return None
    
    # Return role with highest hierarchy level
    return max(roles, key=lambda r: r.hierarchy_level)


def remove_user_role(user, role_code: str, company=None, module=None):
    """
    Remove a role from a user.
    """
    try:
        role = Role.objects.filter(code=role_code, is_active=True).first()
        if not role:
            return False
        
        user_role = UserRole.objects.filter(
            user=user,
            role=role,
            company=company,
            module=module
        ).first()
        
        if user_role:
            user_role.is_active = False
            user_role.save()
            logger.info(f"Removed role {role_code} from user {user.email}")
            return True
        
        return False
    except Exception as e:
        logger.exception(f"Error removing role {role_code} from user {user.email}: {e}")
        return False

