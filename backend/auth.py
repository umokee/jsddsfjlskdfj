from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import os

# API Key для защиты endpoints
# В production храните в переменных окружения или секретном хранилище
API_KEY = os.getenv("TASK_MANAGER_API_KEY", "your-secret-key-change-me")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key for authentication"""
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return api_key
