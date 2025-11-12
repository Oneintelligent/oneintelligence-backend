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
from app.utils.response import api_response

logger = logging.getLogger(__name__)

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
            status_code=1,
            status="failure",
            data={},
            error_code="AUTH_ERROR",
            error_message="Authentication credentials were not provided or invalid."
        )

    # --- Handle Permission Denied ---
    if isinstance(exc, PermissionDenied):
        return api_response(
            status_code=1,
            status="failure",
            data={},
            error_code="PERMISSION_DENIED",
            error_message="You do not have permission to perform this action."
        )

    # --- Handle Validation Errors ---
    if isinstance(exc, ValidationError):
        return api_response(
            status_code=1,
            status="failure",
            data={},
            error_code="VALIDATION_ERROR",
            error_message=exc.detail
        )

    # --- Handle other DRF API Exceptions (like NotFound, ParseError, etc.) ---
    if isinstance(exc, APIException):
        return api_response(
            status_code=1,
            status="failure",
            data={},
            error_code="API_EXCEPTION",
            error_message=str(exc.detail)
        )

    # --- Handle Unexpected Server Errors ---
    logger.exception("Unhandled Exception", exc_info=exc)
    return api_response(
        status_code=1,
        status="failure",
        data={},
        error_code="INTERNAL_SERVER_ERROR",
        error_message=str(exc)
    )
