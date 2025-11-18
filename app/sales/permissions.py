# app/sales/permissions.py
from rest_framework.permissions import BasePermission
from django.conf import settings

def _get_user_id(user):
    # supports either user.userId or user.id
    return str(getattr(user, "userId", None) or getattr(user, "id", None))

def is_platform_admin(user):
    return getattr(user, "role", None) in {"PlatformAdmin", "SuperAdmin"}

def is_admin(user):
    return getattr(user, "role", None) in {"Admin", "Manager", "PlatformAdmin", "SuperAdmin"}

def is_sales_role(user):
    # treat 'User' as possible sales agent in many tenants; update mapping as needed
    return getattr(user, "role", None) in {"Manager", "Admin", "User", "PlatformAdmin", "SuperAdmin"}

def is_support_role(user):
    # add exact support role label if you used a different string (e.g., "SupportAgent")
    return getattr(user, "role", None) in {"SupportAgent", "Support", "Guest"}

def can_view_sales_record(user, record):
    """
    Generic visibility rule:
    - Platform/Admins always allowed
    - User must be same company
    - Visibility:
        owner  -> only owner (or admins)
        team   -> owner, record.team members, admins
        company-> any sales role or admins
        shared -> owner or explicit user in shared_with, or admins
    - Support role: can view only if explicitly shared OR if visibility allows and your tenant policy permits (by default support not allowed on company-level)
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    # Admin override
    if is_platform_admin(user) or is_admin(user):
        return True

    # company check
    user_company = getattr(user, "company_id", None) or getattr(user, "company", None)
    record_company = getattr(record, "company_id", None) or getattr(record, "company", None)
    if str(user_company) != str(record_company):
        return False

    vis = getattr(record, "visibility", "owner")
    user_id = _get_user_id(user)

    # owner visibility
    if vis == "owner":
        owner_id = str(getattr(record, "owner_id", None) or getattr(record, "owner", None) or "")
        return owner_id == user_id

    # team visibility
    if vis == "team":
        # must have team on record and user.team must match or be owner
        record_team = getattr(record, "team_id", None) or getattr(record, "team", None)
        user_team = getattr(user, "team_id", None) or getattr(user, "team", None)
        try:
            # try string compare for uuids
            if record_team and user_team and str(record_team) == str(user_team):
                return True
        except Exception:
            pass
        # owner always allowed
        owner_id = str(getattr(record, "owner_id", None) or getattr(record, "owner", None) or "")
        return owner_id == user_id

    # company visibility
    if vis == "company":
        # company visibility: only sales roles + admins
        if is_sales_role(user):
            return True
        # support not allowed by default for company level
        return False

    # shared visibility
    if vis == "shared":
        shared = getattr(record, "shared_with", []) or []
        if user_id in [str(x) for x in shared]:
            return True
        # owner allowed
        owner_id = str(getattr(record, "owner_id", None) or getattr(record, "owner", None) or "")
        if owner_id == user_id:
            return True
        return False

    return False


class IsSalesRecordVisible(BasePermission):
    """
    DRF permission class for object-level checks on Lead/Opportunity
    """
    def has_object_permission(self, request, view, obj):
        return can_view_sales_record(request.user, obj)

    def has_permission(self, request, view):
        # list/create endpoints will rely on view.get_queryset scoping
        return getattr(request.user, "is_authenticated", False)
