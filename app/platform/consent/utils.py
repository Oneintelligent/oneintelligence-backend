"""
Consent Utility Functions
Helper functions for checking consent
"""

from typing import Optional
from .models import UserConsent, ConsentType


def has_consent(user, consent_type: str, company=None) -> bool:
    """
    Check if user has granted consent for a specific type.
    
    Args:
        user: User instance
        consent_type: Type of consent (from ConsentType)
        company: Optional company for scoping (future use)
    
    Returns:
        bool: True if consent is granted and valid
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    try:
        consent = UserConsent.objects.filter(
            user=user,
            consent_type=consent_type,
            granted=True
        ).first()
        
        if consent:
            return consent.is_valid()
        
        return False
    except Exception:
        return False


def has_ai_consent(user, company=None) -> bool:
    """Check if user has AI usage consent"""
    return has_consent(user, ConsentType.AI_USAGE, company=company)


def has_data_storage_consent(user, company=None) -> bool:
    """Check if user has data storage consent"""
    return has_consent(user, ConsentType.DATA_STORAGE, company=company)


def require_consent(consent_type: str):
    """
    Decorator to require consent for a view.
    Usage:
        @require_consent(ConsentType.AI_USAGE)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            from app.utils.response import api_response
            from rest_framework import status as http_status
            
            if not has_consent(request.user, consent_type):
                return api_response(
                    http_status.HTTP_403_FORBIDDEN,
                    "failure",
                    {},
                    "CONSENT_REQUIRED",
                    f"Consent for {consent_type} is required to use this feature."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

