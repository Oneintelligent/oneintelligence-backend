import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    NotAuthenticated,
    AuthenticationFailed,
    PermissionDenied
)
from rest_framework import status
from rest_framework.serializers import ValidationError as SerializerValidationError
from app.utils.response import api_response

logger = logging.getLogger(__name__)


def format_validation_error(error_detail):
    """
    Convert DRF ValidationError detail into a readable error message.
    
    Handles:
    - Dict format: {'email': [ErrorDetail(...)]} -> "Email: user with this email already exists."
    - List format: [ErrorDetail(...)] -> "user with this email already exists."
    - String format: "error message" -> "error message"
    """
    if isinstance(error_detail, dict):
        # Field-level errors: {'email': [ErrorDetail(...)], 'password': [...]}
        messages = []
        for field, errors in error_detail.items():
            # Extract error strings from ErrorDetail objects
            error_strings = []
            for error in errors:
                if hasattr(error, 'string'):
                    error_strings.append(error.string)
                else:
                    error_strings.append(str(error))
            
            # Format: "Field: error1, error2"
            field_name = field.replace('_', ' ').title()
            messages.append(f"{field_name}: {', '.join(error_strings)}")
        
        return ". ".join(messages)
    
    elif isinstance(error_detail, list):
        # Non-field errors: [ErrorDetail(...), ...]
        messages = []
        for error in error_detail:
            if hasattr(error, 'string'):
                messages.append(error.string)
            else:
                messages.append(str(error))
        return ". ".join(messages)
    
    elif isinstance(error_detail, str):
        # Simple string error
        return error_detail
    
    else:
        # Fallback: convert to string
        return str(error_detail)

def custom_exception_handler(exc, context):
    """
    Custom global exception handler for OneIntelligence.
    Ensures ALL API errors use the api_response() format.
    """
    # Let DRF handle built-in exceptions first (may return a default response)
    response = exception_handler(exc, context)

    view = context.get('view', None)
    view_name = view.__class__.__name__ if view else 'UnknownView'
    logger.error(f"[{view_name}] Exception: {exc}")

    # --- Handle Auth Errors ---
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            status="failure",
            data={},
            error_code="AUTH_ERROR",
            error_message="Authentication credentials were not provided or invalid."
        )

    # --- Handle Permission Denied ---
    if isinstance(exc, PermissionDenied):
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            status="failure",
            data={},
            error_code="PERMISSION_DENIED",
            error_message="You do not have permission to perform this action."
        )

    # --- Handle Validation Errors ---
    if isinstance(exc, (ValidationError, SerializerValidationError)):
        error_message = format_validation_error(exc.detail)
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            status="failure",
            data={},
            error_code="VALIDATION_ERROR",
            error_message=error_message
        )

    # --- Handle other DRF API Exceptions (like NotFound, ParseError, etc.) ---
    if isinstance(exc, APIException):
        error_message = format_validation_error(exc.detail) if hasattr(exc, 'detail') else str(exc)
        return api_response(
            status_code=exc.status_code if hasattr(exc, 'status_code') else status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="API_EXCEPTION",
            error_message=error_message
        )

    # --- Handle Unexpected Server Errors ---
    logger.exception("Unhandled Exception", exc_info=exc)
    return api_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        status="failure",
        data={},
        error_code="INTERNAL_SERVER_ERROR",
        error_message="An unexpected error occurred. Please try again later."
    )
