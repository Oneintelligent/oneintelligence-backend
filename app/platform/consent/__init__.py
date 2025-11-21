"""
Consent Management System
Simple, transparent consent tracking for GDPR compliance
"""

# Lazy imports to avoid circular dependency issues during Django app loading
# Import these within functions/classes when needed, or use:
# from app.platform.consent.models import UserConsent, ConsentType
# from app.platform.consent.utils import has_consent, has_ai_consent, etc.

__all__ = [
    "UserConsent",
    "ConsentType",
    "has_consent",
    "has_ai_consent",
    "has_data_storage_consent",
    "require_consent",
]

