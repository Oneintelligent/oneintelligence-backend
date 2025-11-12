# utils.py
from rest_framework.response import Response

def api_response(status_code=0, status="success", data=None, error_code=None, error_message=None):
    """
    Standardized API response
    """
    return Response({
        "statusCode": status_code,
        "status": status,
        "data": data or {},
        "errorCode": error_code,
        "errorMessage": error_message
    })

