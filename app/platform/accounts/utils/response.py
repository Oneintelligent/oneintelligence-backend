# utils/response.py

def api_response(
    status_code: int = 0,
    status: str = "success",
    data: dict | list | None = None,
    error_code: str = "",
    error_message: str = ""
) -> dict:
    """
    Standard API response format.

    Parameters:
        status_code (int): 0 for success, 1 for errors
        status (str): "success" or "error"
        data (dict or list): Payload data
        error_code (str): Optional error code
        error_message (str): Optional error message

    Returns:
        dict: Formatted API response
    """
    return {
        "statusCode": status_code,
        "status": status,
        "data": data or {},
        "errorCode": error_code,
        "errorMessage": error_message
    }
