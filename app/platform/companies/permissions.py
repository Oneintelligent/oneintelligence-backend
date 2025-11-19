# app/onboarding/companies/permissions.py

def is_platform_admin(user) -> bool:
    """OI internal admin that can modify sensitive fields like discount."""
    try:
        return user.role == user.Role.PLATFORMADMIN
    except Exception:
        return False


def is_owner(user, company) -> bool:
    """Customer workspace SuperAdmin."""
    try:
        return str(user.userId) == str(company.created_by_user_id)
    except Exception:
        return False


def is_company_admin(user, company) -> bool:
    """Customer Admin (not including SuperAdmin)."""
    try:
        if user.role == user.Role.ADMIN:
            return str(user.companyId) == str(company.companyId)
        if getattr(user, "is_superuser", False):
            return True
    except Exception:
        pass
    return False
