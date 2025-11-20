# app/workspace/tasks/permissions.py
from django.db.models import Q
from .models import Task


def can_view_task(user, task):
    """Check if user can view a task."""
    # Platform admins can view all
    if hasattr(user, "role") and user.role in ["PlatformAdmin", "SuperAdmin"]:
        return True
    
    # Must be in same company
    if task.company_id != user.company_id:
        return False
    
    # Owner or assignee can always view
    if task.owner_id == user.userId or task.assignee_id == user.userId:
        return True
    
    # Check visibility and sharing
    if task.visibility == "company":
        return True
    
    if task.visibility == "team" and task.team_id and user.team_id == task.team_id:
        return True
    
    if task.visibility == "shared" and str(user.userId) in task.shared_with:
        return True
    
    return False


def can_edit_task(user, task):
    """Check if user can edit a task."""
    if not can_view_task(user, task):
        return False
    
    # Owner or assignee can edit
    if task.owner_id == user.userId or task.assignee_id == user.userId:
        return True
    
    return False


def can_delete_task(user, task):
    """Check if user can delete a task."""
    # Only owner or platform admin
    if hasattr(user, "role") and user.role in ["PlatformAdmin", "SuperAdmin"]:
        return True
    
    return task.owner_id == user.userId

