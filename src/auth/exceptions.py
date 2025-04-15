from typing import NoReturn

from fastapi import HTTPException, status


def raise_invalid_token_error(detail: str) -> NoReturn:
    """Raise HTTP 400 Bad Request error for invalid tokens."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def raise_conflict_error(detail: str) -> NoReturn:
    """Raise HTTP 409 Conflict error for resource conflicts."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def raise_unauthorized_error(detail: str) -> NoReturn:
    """Raise HTTP 401 Unauthorized error for authentication failures."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def raise_not_found_error(detail: str) -> NoReturn:
    """Raise HTTP 404 Not Found error for missing resources."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def raise_forbidden_error(detail: str) -> NoReturn:
    """Raise HTTP 403 Forbidden error for unauthorized access."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def raise_plaid_api_error(error: Exception) -> NoReturn:
    """Raise HTTP 500 Internal Server Error for Plaid API errors."""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Plaid API error: {error!s}",
    ) from error


def raise_invalid_data_error(error: Exception) -> NoReturn:
    """Raise HTTP 400 Bad Request error for invalid data."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid data: {error!s}",
    ) from error


def raise_missing_field_error(field_name: str) -> NoReturn:
    """Raise HTTP 400 Bad Request error for missing required fields."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"{field_name} is required",
    )
