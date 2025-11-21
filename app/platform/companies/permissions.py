# app/platform/companies/permissions.py
"""
Company permissions using RBAC system.
"""

from app.platform.rbac.utils import (
    is_platform_admin as rbac_is_platform_admin,
    is_super_admin as rbac_is_super_admin,
    is_company_admin as rbac_is_company_admin,
)


def is_platform_admin(user) -> bool:
    """Check if user is a platform admin using RBAC."""
    return rbac_is_platform_admin(user)


def is_owner(user, company) -> bool:
    """Check if user is the company owner (Super Admin) using RBAC."""
    return rbac_is_super_admin(user, company=company)


def is_company_admin(user, company) -> bool:
    """Check if user is a company admin using RBAC."""
    return rbac_is_company_admin(user, company=company)
