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
