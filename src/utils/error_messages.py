"""Error messages used across the application."""

# OpenAI errors
OPENAI_ERROR_MESSAGE = "OpenAI error: {}"
OPENAI_KEY_MISSING = "❌ OPENAI_API_KEY is not set in environment variables"

# User errors
USER_ID_REQUIRED = "User ID is required"

__all__ = [
    "OPENAI_ERROR_MESSAGE",
    "OPENAI_KEY_MISSING",
    "USER_ID_REQUIRED",
]
