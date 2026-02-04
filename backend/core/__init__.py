"""
Core infrastructure module.
Contains database connection, base exceptions, and security.
No business logic here.
"""

from .database import Base, SessionLocal, engine, get_db
from .exceptions import (
    AppError,
    NotFoundError,
    ValidationError,
    DatabaseError,
    BackupError,
)
from .security import verify_api_key, get_api_key

__all__ = [
    # Database
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    # Exceptions
    "AppError",
    "NotFoundError",
    "ValidationError",
    "DatabaseError",
    "BackupError",
    # Security
    "verify_api_key",
    "get_api_key",
]
