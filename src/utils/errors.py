from fastapi import HTTPException, status


def raise_invalid_token_error(detail: str) -> None:
    """Raise HTTP 400 Bad Request error for invalid tokens."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def raise_conflict_error(detail: str) -> None:
    """Raise HTTP 409 Conflict error for resource conflicts."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )
