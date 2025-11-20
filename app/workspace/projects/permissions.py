# app/workspace/projects/permissions.py
from django.db.models import Q
from .models import Project, ProjectMember


def can_view_project(user, project):
    """Check if user can view a project."""
    # Platform admins can view all
    if hasattr(user, "role") and user.role in ["PlatformAdmin", "SuperAdmin"]:
        return True
    
    # Must be in same company
    if project.company_id != user.company_id:
        return False
    
    # Owner can always view
    if project.owner_id == user.userId:
        return True
    
    # Check if user is a member
    if ProjectMember.objects.filter(project=project, user=user).exists():
        return True
    
    # Check visibility and sharing
    if project.visibility == "company":
        return True
    
    if project.visibility == "team" and project.team_id and user.team_id == project.team_id:
        return True
    
    if project.visibility == "shared" and str(user.userId) in project.shared_with:
        return True
    
    return False


def can_edit_project(user, project):
    """Check if user can edit a project."""
    if not can_view_project(user, project):
        return False
    
    # Owner can always edit
    if project.owner_id == user.userId:
        return True
    
    # Check member role
    member = ProjectMember.objects.filter(project=project, user=user).first()
    if member and member.role in ["owner", "manager"]:
        return True
    
    return False


def can_delete_project(user, project):
    """Check if user can delete a project."""
    # Only owner or platform admin
    if hasattr(user, "role") and user.role in ["PlatformAdmin", "SuperAdmin"]:
        return True
    
    return project.owner_id == user.userId

