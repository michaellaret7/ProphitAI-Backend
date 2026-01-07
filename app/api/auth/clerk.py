"""
Clerk JWT Authentication

Validates Clerk session tokens from frontend and extracts user identity.
"""

import os
import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from clerk_backend_api import Clerk
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# JWKS URL from Clerk Dashboard → API Keys → JWKS URL
# Format: https://<your-instance>.clerk.accounts.dev/.well-known/jwks.json
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

logger.info(f"🔐 Clerk Auth Config:")
logger.info(f"   JWKS URL: {CLERK_JWKS_URL}")
logger.info(f"   Secret Key: {CLERK_SECRET_KEY[:20] if CLERK_SECRET_KEY else 'NOT SET'}...")
logger.info(f"   Debug Mode: {DEBUG}")

# Configure JWT validation
clerk_config = ClerkConfig(
    jwks_url=CLERK_JWKS_URL,
    leeway=5.0  # 5 second clock drift tolerance
)

clerk_auth = ClerkHTTPBearer(config=clerk_config, debug_mode=True)  # Force debug mode

# Official SDK for admin operations
def get_clerk_client() -> Clerk:
    return Clerk(bearer_auth=CLERK_SECRET_KEY)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(clerk_auth)
) -> dict:
    """
    Extract authenticated user from Clerk JWT.

    Returns decoded token payload with user info:
    - sub: Clerk user ID
    - email: User's email (if available in token)
    - etc.
    """
    return credentials.decoded


async def get_clerk_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(clerk_auth)
) -> str:
    """Extract just the Clerk user ID from token."""
    logger.info(f"🔓 Token validated successfully!")
    logger.info(f"   Decoded payload: {credentials.decoded}")
    return credentials.decoded.get("sub")
