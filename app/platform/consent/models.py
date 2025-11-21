"""
Consent Management Models
Simple, transparent consent tracking for GDPR and privacy compliance
"""

from django.db import models
from django.contrib.auth import get_user_model
from app.core.models import CoreBaseModel

User = get_user_model()


class ConsentType(models.TextChoices):
    """Types of consent we track"""
    AI_USAGE = "ai_usage", "AI Usage"
    DATA_STORAGE = "data_storage", "Data Storage"
    MARKETING = "marketing", "Marketing Communications"
    ANALYTICS = "analytics", "Analytics & Tracking"


class UserConsent(CoreBaseModel):
    """
    Tracks user consent for various purposes.
    Simple, transparent, GDPR-compliant.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="consents",
        db_index=True
    )
    
    consent_type = models.CharField(
        max_length=50,
        choices=ConsentType.choices,
        db_index=True,
        help_text="Type of consent"
    )
    
    granted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether consent is granted"
    )
    
    granted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When consent was granted"
    )
    
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When consent was revoked"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address when consent was given"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent when consent was given"
    )
    
    consent_text = models.TextField(
        blank=True,
        help_text="The exact text the user consented to"
    )
    
    version = models.CharField(
        max_length=20,
        default="1.0",
        help_text="Version of consent text"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    
    class Meta:
        db_table = "platform_user_consents"
        unique_together = [("user", "consent_type")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "consent_type"]),
            models.Index(fields=["user", "granted"]),
        ]
    
    def __str__(self):
        status = "Granted" if self.granted else "Revoked"
        return f"{self.user.email} - {self.get_consent_type_display()} - {status}"
    
    def grant(self, ip_address=None, user_agent=None, consent_text=None, version="1.0"):
        """Grant consent"""
        from django.utils import timezone
        self.granted = True
        self.granted_at = timezone.now()
        self.revoked_at = None
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
        if consent_text:
            self.consent_text = consent_text
        self.version = version
        self.save(update_fields=[
            "granted", "granted_at", "revoked_at", "ip_address", 
            "user_agent", "consent_text", "version", "updated_at"
        ])
    
    def revoke(self):
        """Revoke consent"""
        from django.utils import timezone
        self.granted = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["granted", "revoked_at", "updated_at"])
    
    def is_valid(self):
        """Check if consent is currently valid"""
        return self.granted and self.revoked_at is None

