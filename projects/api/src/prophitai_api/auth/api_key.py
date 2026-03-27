"""
API Key Authentication

Provides header-based API key authentication for FastAPI endpoints.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import os
from dotenv import load_dotenv

# Reason: Load environment variables before reading PROPHITAI_API_KEYS
load_dotenv()

# Extract API keys from environment variable
# PROPHITAI_API_KEYS should be a comma-separated list in .env file
PROPHITAI_API_KEYS = set(key.strip() for key in os.getenv("PROPHITAI_API_KEYS", "").split(",") if key.strip())

# Define the header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate API key from X-API-Key header.

    Args:
        api_key: API key from request header

    Returns:
        The validated API key

    Raises:
        HTTPException: 401 if API key is invalid or missing
    """
    # Reason: Fail fast if server is misconfigured
    if not PROPHITAI_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API keys not configured on server"
        )

    # Reason: Check if provided key is in the set of valid keys
    if api_key not in PROPHITAI_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
