"""
Authentication and security utilities.
"""
from fastapi import HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader
import os
import logging

# Configure logging for fail2ban integration
logger = logging.getLogger("task_manager.auth")

# API Key for protecting endpoints
# In production, store in environment variables or secret manager
API_KEY = os.getenv("TASK_MANAGER_API_KEY", "your-secret-key-change-me")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> str:
    """Get the configured API key."""
    return API_KEY


async def verify_api_key(
    request: Request,
    api_key: str = Security(api_key_header)
):
    """Verify API key for authentication."""
    if not api_key or api_key != API_KEY:
        # Log failed attempt with client IP for fail2ban
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(f"Invalid API key attempt from {client_ip}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return api_key
