"""
Consent Management API
Simple, transparent consent management for GDPR compliance
"""

import logging
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from app.utils.response import api_response
from app.utils.exception_handler import format_validation_error
from app.platform.consent.models import UserConsent, ConsentType
from app.platform.consent.serializers import (
    UserConsentSerializer,
    ConsentUpdateSerializer,
    ConsentStatusSerializer
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["Consent"])
class ConsentViewSet(viewsets.ViewSet):
    """
    Consent management endpoints.
    Simple, transparent consent tracking for GDPR compliance.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_user_agent(self, request):
        """Get user agent"""
        return request.META.get('HTTP_USER_AGENT', '')
    
    @extend_schema(
        summary="Get user consent status",
        description="Returns current consent status for all consent types"
    )
    @action(detail=False, methods=["get"], url_path="status")
    def get_status(self, request):
        """Get consent status for authenticated user"""
        try:
            user = request.user
            
            # Get all consents for user
            consents = UserConsent.objects.filter(user=user)
            consent_dict = {c.consent_type: c.is_valid() for c in consents}
            
            # Get last updated timestamp
            last_updated = None
            if consents.exists():
                last_consent = consents.order_by("-last_updated_date").first()
                last_updated = last_consent.last_updated_date
            
            data = {
                "ai_usage": consent_dict.get(ConsentType.AI_USAGE, False),
                "data_storage": consent_dict.get(ConsentType.DATA_STORAGE, False),
                "marketing": consent_dict.get(ConsentType.MARKETING, False),
                "analytics": consent_dict.get(ConsentType.ANALYTICS, False),
            }
            
            if last_updated:
                data["last_updated"] = last_updated
            
            return api_response(200, "success", data)
            
        except Exception as exc:
            logger.exception(f"Error getting consent status: {exc}")
            return api_response(
                500, "failure", {},
                "SERVER_ERROR",
                "An error occurred while retrieving consent status"
            )
    
    @extend_schema(
        summary="Get all user consents",
        description="Returns detailed consent records for the user"
    )
    @action(detail=False, methods=["get"], url_path="all")
    def get_all(self, request):
        """Get all consent records for user"""
        try:
            user = request.user
            consents = UserConsent.objects.filter(user=user).order_by("-created_date")
            serializer = UserConsentSerializer(consents, many=True)
            return api_response(200, "success", {"consents": serializer.data})
            
        except Exception as exc:
            logger.exception(f"Error getting consents: {exc}")
            return api_response(
                500, "failure", {},
                "SERVER_ERROR",
                "An error occurred while retrieving consents"
            )
    
    @extend_schema(
        summary="Update consent",
        description="Grant or revoke consent for a specific type"
    )
    @action(detail=False, methods=["post"], url_path="update")
    def update_consent(self, request):
        """Update user consent"""
        try:
            user = request.user
            serializer = ConsentUpdateSerializer(data=request.data)
            
            if not serializer.is_valid():
                error_message = format_validation_error(serializer.errors)
                return api_response(
                    400, "failure", {},
                    "VALIDATION_ERROR",
                    error_message
                )
            
            consent_type = serializer.validated_data["consent_type"]
            granted = serializer.validated_data["granted"]
            consent_text = serializer.validated_data.get("consent_text", "")
            
            # Get or create consent record
            consent, created = UserConsent.objects.get_or_create(
                user=user,
                consent_type=consent_type,
                defaults={}
            )
            
            # Default consent text if not provided
            if not consent_text:
                consent_text = self._get_default_consent_text(consent_type)
            
            # Update consent
            if granted:
                consent.grant(
                    ip_address=self._get_client_ip(request),
                    user_agent=self._get_user_agent(request),
                    consent_text=consent_text,
                    version="1.0"
                )
                action = "granted"
            else:
                consent.revoke()
                action = "revoked"
            
            logger.info(
                f"User {user.email} {action} consent for {consent_type}"
            )
            
            serializer = UserConsentSerializer(consent)
            return api_response(
                200, "success",
                {
                    "consent": serializer.data,
                    "message": f"Consent {action} successfully"
                }
            )
            
        except Exception as exc:
            logger.exception(f"Error updating consent: {exc}")
            return api_response(
                500, "failure", {},
                "SERVER_ERROR",
                "An error occurred while updating consent"
            )
    
    def _get_default_consent_text(self, consent_type):
        """Get default consent text for each type"""
        texts = {
            ConsentType.AI_USAGE: (
                "I consent to using OneIntelligence AI features. "
                "This includes processing my data through AI models to provide "
                "intelligent insights, recommendations, and assistance. "
                "My conversations and data will be stored securely and used only "
                "to improve my experience."
            ),
            ConsentType.DATA_STORAGE: (
                "I consent to storing my data in the OneIntelligence platform. "
                "This includes my profile information, workspace data, projects, "
                "tasks, and other content I create. My data will be stored securely "
                "and used only to provide the services I've requested."
            ),
            ConsentType.MARKETING: (
                "I consent to receiving marketing communications from OneIntelligence, "
                "including product updates, newsletters, and promotional content. "
                "I can unsubscribe at any time."
            ),
            ConsentType.ANALYTICS: (
                "I consent to the use of analytics and tracking to improve "
                "the OneIntelligence platform. This helps us understand how "
                "features are used and make improvements."
            ),
        }
        return texts.get(consent_type, "I consent to the use of this feature.")

