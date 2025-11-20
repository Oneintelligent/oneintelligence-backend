# app/workspace/support/permissions.py
from django.db.models import Q


def can_view_ticket(user, ticket):
    """Check if user can view a ticket."""
    # Must be in same company
    if ticket.company_id != user.company_id:
        return False
    
    # Owner can always view
    if ticket.owner_id == user.userId:
        return True
    
    # Assignee can view
    if ticket.assignee_id == user.userId:
        return True
    
    # Company-wide visibility
    if ticket.visibility == "company":
        return True
    
    # Team visibility
    if ticket.visibility == "team" and ticket.team_id and user.team_id == ticket.team_id:
        return True
    
    # Shared visibility
    if ticket.visibility == "shared" and str(user.userId) in ticket.shared_with:
        return True
    
    # Creator can view
    if ticket.created_by_id == user.userId:
        return True
    
    return False


def can_edit_ticket(user, ticket):
    """Check if user can edit a ticket."""
    if not can_view_ticket(user, ticket):
        return False
    
    # Owner can always edit
    if ticket.owner_id == user.userId:
        return True
    
    # Assignee can edit
    if ticket.assignee_id == user.userId:
        return True
    
    # Creator can edit
    if ticket.created_by_id == user.userId:
        return True
    
    # TODO: Add role-based permissions (admin, support manager, etc.)
    return False


def can_delete_ticket(user, ticket):
    """Check if user can delete a ticket."""
    # Must be in same company
    if ticket.company_id != user.company_id:
        return False
    
    # Only owner or creator can delete
    if ticket.owner_id == user.userId:
        return True
    
    if ticket.created_by_id == user.userId:
        return True
    
    # TODO: Add admin role check
    return False

