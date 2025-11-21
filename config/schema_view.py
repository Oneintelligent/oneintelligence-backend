"""
Custom schema view with error handling for drf-spectacular
"""
import logging
from drf_spectacular.views import SpectacularAPIView
from rest_framework.response import Response
from rest_framework import status, permissions
from app.utils.response import api_response

logger = logging.getLogger(__name__)


class CustomSpectacularAPIView(SpectacularAPIView):
    """
    Custom schema view that handles errors gracefully
    Schema endpoint should be public (no authentication required)
    """
    permission_classes = [permissions.AllowAny]  # Make schema public
    
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.exception(f"Error generating OpenAPI schema: {e}")
            # Return a helpful error message
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="failure",
                data={},
                error_code="SCHEMA_GENERATION_ERROR",
                error_message=f"Failed to generate API schema: {str(e)}. Check server logs for details."
            )

